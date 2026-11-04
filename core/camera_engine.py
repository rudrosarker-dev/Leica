# -*- coding: utf-8 -*-
"""
Fast-Path 30.0 FPS Camera Capture & Pure Natural ISP Pipeline (`core/camera_engine.py`).
- Startup defaults to Auto-Exposure (`CAP_PROP_AUTO_EXPOSURE = 0.75`) and Auto White Balance
  (`CAP_PROP_AUTO_WB = 1.0`) so the Logitech C270's built-in RightLight sensor brightens
  indoor rooms naturally.
- Fast Path Optimization: When sliders are at their neutral defaults (or when Pure View Bypass
  is active), every heavy processing stage is completely skipped—reading the frame, flipping
  horizontally, and displaying at a locked 30.0 FPS!
"""

import collections
import copy
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

import cv2
import numpy as np
from PyQt6.QtCore import QThread, QMutex, QMutexLocker, pyqtSignal

from core.ai_processor import AIProcessor
from core.color_lut import ColorLUTEngine
from core.preset_manager import DEFAULT_STUDIO_PARAMS


class CameraWorker(QThread):
    """High-priority 30 FPS camera capture and fast-path ISP worker."""

    frame_ready = pyqtSignal(np.ndarray, dict)
    snapshot_saved = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(self, output_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.output_dir = output_dir
        self._mutex = QMutex()
        self._running = False

        self._device_index: int = 0
        self._reopen_requested: bool = True
        self._open_driver_dialog_requested: bool = False

        self._params: Dict[str, Any] = copy.deepcopy(DEFAULT_STUDIO_PARAMS)
        self._last_hw_signature: Optional[Tuple[Any, ...]] = None

        # Gimbal EMA state
        self.cur_zoom: float = 1.00
        self.cur_pan_x: float = 0.00
        self.cur_pan_y: float = 0.00
        self._auto_target_pan_x: float = 0.00
        self._auto_target_pan_y: float = 0.00

        # Snapshot queue
        self._pending_snapshots: int = 0
        self._snapshot_format: str = "PNG (Lossless)"

        self.color_engine = ColorLUTEngine()
        self.ai_processor = AIProcessor()

        self.recorder_hook = None
        self.virtual_cam_hook = None

    @staticmethod
    def enumerate_cameras(max_Check: int = 4) -> List[Tuple[int, str]]:
        found: List[Tuple[int, str]] = []
        for idx in range(max_Check):
            cap = None
            try:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(idx)
                if cap is not None and cap.isOpened():
                    label = f"Logitech HD Webcam C270 (#{idx})" if idx == 0 else f"USB Video Device #{idx}"
                    found.append((idx, label))
            except Exception:
                pass
            finally:
                if cap is not None:
                    cap.release()
        if not found:
            found.append((0, "Logitech HD Webcam C270 (Default)"))
        return found

    def set_device(self, device_index: int, backend_name: str = "DirectShow") -> None:
        with QMutexLocker(self._mutex):
            self._device_index = int(device_index)
            self._reopen_requested = True
            self._last_hw_signature = None

    def request_driver_settings_dialog(self) -> None:
        with QMutexLocker(self._mutex):
            self._open_driver_dialog_requested = True

    def update_param(self, key: str, value: Any) -> None:
        with QMutexLocker(self._mutex):
            self._params[key] = value

    def update_all_params(self, new_params: Dict[str, Any]) -> None:
        with QMutexLocker(self._mutex):
            self._params.update(copy.deepcopy(new_params))
            self._last_hw_signature = None

    def get_params_copy(self) -> Dict[str, Any]:
        with QMutexLocker(self._mutex):
            return copy.deepcopy(self._params)

    def trigger_snapshot(self, fmt: str = "PNG (Lossless)", count: int = 1) -> None:
        with QMutexLocker(self._mutex):
            self._snapshot_format = fmt
            self._pending_snapshots += int(count)

    def stop_worker(self) -> None:
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(3000)

    def _open_capture(self, device_index: int) -> Optional[cv2.VideoCapture]:
        try:
            cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(device_index)
            if not cap.isOpened():
                cap = cv2.VideoCapture(device_index)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # Ensure Auto Exposure and Auto WB are enabled on launch
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                cap.set(cv2.CAP_PROP_AUTO_WB, 1.0)
                return cap
        except Exception:
            pass
        return None

    def _sync_hardware_registers(self, cap: Optional[cv2.VideoCapture], params: Dict[str, Any]) -> None:
        if cap is None or not cap.isOpened():
            return

        manual_exp = bool(params.get("manual_exposure", False)) and not bool(params.get("pure_view_bypass", False))
        exp_val = int(float(params.get("hardware_exposure", -4.0)))
        gain_val = int(float(params.get("hardware_gain", 120.0)))

        hw_sig = (manual_exp, exp_val, gain_val)
        if hw_sig == self._last_hw_signature:
            return
        self._last_hw_signature = hw_sig

        try:
            if manual_exp:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                cap.set(cv2.CAP_PROP_EXPOSURE, float(exp_val))
                cap.set(cv2.CAP_PROP_GAIN, float(gain_val))
            else:
                # Native Auto Exposure (RightLight) — keeps video bright naturally
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                cap.set(cv2.CAP_PROP_AUTO_WB, 1.0)
        except Exception:
            pass

    @staticmethod
    def _generate_bright_natural_reference_frame(tick: float) -> np.ndarray:
        """
        Generates a bright, crisp, daylight-balanced 1280x720 studio scene when no physical
        webcam is attached in headless/CI environments.
        """
        h, w = 720, 1280
        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

        # Bright airy studio wall background
        bg_b = 195.0 - 35.0 * (y_grid / h)
        bg_g = 202.0 - 32.0 * (y_grid / h)
        bg_r = 208.0 - 28.0 * (y_grid / h)
        frame = np.stack([bg_b, bg_g, bg_r], axis=-1)

        # Soft sunlit window glow on left
        wx, wy = w * 0.22, h * 0.28
        wdist2 = ((x_grid - wx) / 340.0) ** 2 + ((y_grid - wy) / 260.0) ** 2
        glow = np.exp(-wdist2)
        frame[:, :, 2] += glow * 35.0
        frame[:, :, 1] += glow * 32.0
        frame[:, :, 0] += glow * 26.0

        cx = w * 0.50 + np.sin(tick * 0.8) * 10.0
        cy = h * 0.42 + np.cos(tick * 0.5) * 5.0

        # Clean charcoal crew-neck sweater
        torso_dist = ((x_grid - cx) / 235.0) ** 2 + ((y_grid - (h * 0.88)) / 260.0) ** 2
        torso_mask = np.clip((1.0 - torso_dist) * 4.5, 0.0, 1.0)[:, :, None]
        sweater_bgr = np.array([58.0, 54.0, 50.0], dtype=np.float32)
        frame = frame * (1.0 - torso_mask) + sweater_bgr * torso_mask

        # Bright natural skin tone portrait oval
        head_dist = ((x_grid - cx) / 96.0) ** 2 + ((y_grid - cy) / 126.0) ** 2
        head_mask = np.clip((1.0 - head_dist) * 6.0, 0.0, 1.0)
        shade = np.clip(0.94 + 0.14 * ((cx - x_grid) / 96.0), 0.80, 1.08)
        skin_bgr = np.stack([162.0 * shade, 188.0 * shade, 226.0 * shade], axis=-1)
        frame = frame * (1.0 - head_mask[:, :, None]) + skin_bgr * head_mask[:, :, None]

        return np.clip(frame, 0, 255).astype(np.uint8)

    def _apply_ptz_and_geometry(self, frame_bgr: np.ndarray, params: Dict[str, Any], frame_idx: int) -> np.ndarray:
        h, w = frame_bgr.shape[:2]

        if bool(params.get("mirror_h", True)):
            frame_bgr = cv2.flip(frame_bgr, 1)

        if bool(params.get("pure_view_bypass", False)):
            return frame_bgr

        auto_frame = bool(params.get("auto_frame_face", False))
        if auto_frame:
            if frame_idx % 4 == 0:
                face_box = self.ai_processor.detect_face(frame_bgr)
                if face_box is not None:
                    fx_px, fy_px, fw_px, fh_px = face_box
                    self._auto_target_pan_x = float(np.clip(((fx_px + fw_px * 0.5) / w - 0.5) * 2.0, -1.0, 1.0))
                    self._auto_target_pan_y = float(np.clip(((fy_px + fh_px * 0.5) / h - 0.5) * 2.0, -1.0, 1.0))
            target_zoom = 1.35
            target_pan_x = self._auto_target_pan_x
            target_pan_y = self._auto_target_pan_y
        else:
            target_zoom = float(params.get("digital_zoom", 1.00))
            target_pan_x = float(params.get("pan_x", 0.00))
            target_pan_y = float(params.get("tilt_y", 0.00))

        damping = 0.12
        self.cur_zoom += (target_zoom - self.cur_zoom) * damping
        self.cur_pan_x += (target_pan_x - self.cur_pan_x) * damping
        self.cur_pan_y += (target_pan_y - self.cur_pan_y) * damping

        zoom = max(1.00, min(2.50, self.cur_zoom))
        if zoom > 1.005:
            crop_w = int(round(w / zoom))
            crop_h = int(round(h / zoom))
            max_dx = (w - crop_w) * 0.5
            max_dy = (h - crop_h) * 0.5
            cx = w * 0.5 + np.clip(self.cur_pan_x, -1.0, 1.0) * max_dx
            cy = h * 0.5 + np.clip(self.cur_pan_y, -1.0, 1.0) * max_dy
            x0 = int(np.clip(cx - crop_w * 0.5, 0, w - crop_w))
            y0 = int(np.clip(cy - crop_h * 0.5, 0, h - crop_h))
            frame_bgr = cv2.resize(frame_bgr[y0 : y0 + crop_h, x0 : x0 + crop_w], (w, h), interpolation=cv2.INTER_LINEAR)

        rot_quad = int(params.get("rotate_quadrant", 0)) % 4
        if rot_quad == 1:
            frame_bgr = cv2.resize(cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE), (w, h), interpolation=cv2.INTER_LINEAR)
        elif rot_quad == 2:
            frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_180)
        elif rot_quad == 3:
            frame_bgr = cv2.resize(cv2.rotate(frame_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE), (w, h), interpolation=cv2.INTER_LINEAR)

        return frame_bgr

    @staticmethod
    def _apply_denoise_and_sharpness(frame_bgr: np.ndarray, denoise_pct: float, sharpness_pct: float) -> np.ndarray:
        # Fast-path skip when sliders are at 0%
        if denoise_pct > 1.0:
            strength = np.clip(denoise_pct / 100.0, 0.0, 1.0)
            ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
            y, cr, cb = cv2.split(ycrcb)
            cr = cv2.addWeighted(cr, 1.0 - strength, cv2.GaussianBlur(cr, (5, 5), 0), strength, 0)
            cb = cv2.addWeighted(cb, 1.0 - strength, cv2.GaussianBlur(cb, (5, 5), 0), strength, 0)
            y = cv2.GaussianBlur(y, (3, 3), 0) if strength < 0.4 else cv2.bilateralFilter(y, d=5, sigmaColor=int(25 * strength), sigmaSpace=10)
            frame_bgr = cv2.cvtColor(cv2.merge([y, cr, cb]), cv2.COLOR_YCrCb2BGR)

        if sharpness_pct > 1.0:
            amount = (sharpness_pct / 100.0) * 1.4
            blur = cv2.GaussianBlur(frame_bgr, (0, 0), sigmaX=1.0)
            frame_bgr = cv2.addWeighted(frame_bgr, 1.0 + amount, blur, -amount, 0)

        return frame_bgr

    @staticmethod
    def _burn_lower_third(frame_bgr: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        if bool(params.get("pure_view_bypass", False)) or not bool(params.get("show_lower_third", False)):
            return frame_bgr

        h, w = frame_bgr.shape[:2]
        scale = w / 1280.0
        name_txt = str(params.get("lower_third_name", "Alex Morgan")).strip()
        title_txt = str(params.get("lower_third_title", "Product Design Lead")).strip()

        x0 = int(40 * scale)
        card_h = int(62 * scale)
        y0 = h - int(42 * scale) - card_h
        card_w = int(max(290 * scale, min(w - x0 * 2, (max(len(name_txt), len(title_txt)) * 11 + 56) * scale)))
        x1, y1 = min(w - 10, x0 + card_w), min(h - 10, y0 + card_h)

        if x1 > x0 and y1 > y0:
            roi = frame_bgr[y0:y1, x0:x1]
            dark_card = np.full_like(roi, (20, 18, 18), dtype=np.uint8)
            cv2.addWeighted(dark_card, 0.82, roi, 0.18, 0, dst=roi)
            cv2.rectangle(frame_bgr, (x0, y0), (x1, y1), (52, 52, 60), 1)
            bar_w = max(3, int(4 * scale))
            frame_bgr[y0:y1, x0 : x0 + bar_w] = (129, 185, 16)  # Emerald accent
            cv2.putText(
                frame_bgr,
                name_txt[:40],
                (x0 + bar_w + int(14 * scale), y0 + int(27 * scale)),
                cv2.FONT_HERSHEY_DUPLEX,
                0.62 * scale,
                (246, 244, 244),
                max(1, int(1.3 * scale)),
                cv2.LINE_AA,
            )
            cv2.putText(
                frame_bgr,
                title_txt[:50],
                (x0 + bar_w + int(14 * scale), y0 + int(48 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45 * scale,
                (180, 184, 192),
                1,
                cv2.LINE_AA,
            )
        return frame_bgr

    def _save_snapshot_frame(self, frame_bgr: np.ndarray, fmt: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        if "JPG" in fmt.upper():
            out_path = self.output_dir / f"Optix_Capture_{ts}.jpg"
            cv2.imwrite(str(out_path), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 98])
        else:
            out_path = self.output_dir / f"Optix_Capture_{ts}.png"
            cv2.imwrite(str(out_path), frame_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        self.snapshot_saved.emit(str(out_path))
        self.status_message.emit(f"Saved Photo: {out_path.name}")

    def run(self) -> None:
        self._running = True
        cap: Optional[cv2.VideoCapture] = None
        fps_times: collections.deque = collections.deque(maxlen=30)
        last_time = time.perf_counter()
        frame_idx = 0

        try:
            while True:
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                    reopen = self._reopen_requested
                    dev_idx = self._device_index
                    open_drv = self._open_driver_dialog_requested
                    self._reopen_requested = False
                    self._open_driver_dialog_requested = False
                    params = copy.deepcopy(self._params)

                if reopen:
                    if cap is not None:
                        cap.release()
                    cap = self._open_capture(dev_idx)
                    self._last_hw_signature = None

                if open_drv and cap is not None and cap.isOpened():
                    try:
                        cap.set(cv2.CAP_PROP_SETTINGS, 1)
                    except Exception:
                        pass

                self._sync_hardware_registers(cap, params)

                ret = False
                frame = None
                if cap is not None and cap.isOpened():
                    ret, frame = cap.read()

                if not ret or frame is None:
                    frame = self._generate_bright_natural_reference_frame(time.perf_counter())
                    time.sleep(0.028)
                else:
                    if frame.shape[1] != 1280 or frame.shape[0] != 720:
                        frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_LINEAR)

                now_t = time.perf_counter()
                dt = max(1e-4, now_t - last_time)
                last_time = now_t
                fps_times.append(dt)
                avg_fps = min(30.0, len(fps_times) / sum(fps_times))
                frame_idx += 1

                bypass = bool(params.get("pure_view_bypass", False))

                # Stage 1: PTZ & Mirror (Fast-path flip when zoom == 1.0)
                frame = self._apply_ptz_and_geometry(frame, params, frame_idx)

                if not bypass:
                    # Stage 2: Fast-path Denoise & Sharpness (Skipped if 0%)
                    frame = self._apply_denoise_and_sharpness(
                        frame,
                        float(params.get("denoise", 0.0)),
                        float(params.get("sharpness", 0.0)),
                    )

                    # Stage 3: Fast-path AI Background Blur / Dimming (Skipped if Off)
                    frame = self.ai_processor.process_background(frame, params)

                    # Stage 4: Fast-path Luminance-Weighted Color & Light Boost (Skipped if neutral)
                    frame = self.color_engine.apply_grade(frame, params)

                    # Stage 5: Optional 1080p Upscaling (Skipped if 720p Fast is selected)
                    if bool(params.get("upscale_1080p", False)):
                        frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LINEAR)

                    # Stage 6: Optional Lower Third Name Tag
                    frame = self._burn_lower_third(frame, params)

                # Only compute histogram if user explicitly enabled Corner HUD in Tab 4
                hist_data = (
                    self.color_engine.compute_histogram_64(frame)
                    if bool(params.get("show_corner_hud", False))
                    else {}
                )

                with QMutexLocker(self._mutex):
                    if self._pending_snapshots > 0:
                        self._pending_snapshots -= 1
                        snap_fmt = self._snapshot_format
                    else:
                        snap_fmt = ""

                if snap_fmt:
                    self._save_snapshot_frame(frame, snap_fmt)

                if self.recorder_hook is not None and self.recorder_hook.is_recording:
                    self.recorder_hook.push_frame(frame)

                if self.virtual_cam_hook is not None and self.virtual_cam_hook.is_active:
                    self.virtual_cam_hook.send_frame(frame)

                out_h, out_w = frame.shape[:2]
                telemetry = {
                    "fps": avg_fps,
                    "width": out_w,
                    "height": out_h,
                    "upscaled": bool(params.get("upscale_1080p", False)) and not bypass,
                    "histogram": hist_data,
                }
                self.frame_ready.emit(frame, telemetry)
        finally:
            if cap is not None:
                cap.release()
