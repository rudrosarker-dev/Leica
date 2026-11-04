# -*- coding: utf-8 -*-
"""
Threaded Camera Capture, C270 30-FPS DirectShow Hardware Controller, and 10-Stage
Optical ISP Pipeline (`core/camera_engine.py`).
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
    """
    High-priority QThread executing DirectShow/MSMF hardware capture and the
    10-stage ISP pipeline at 30 FPS without blocking the PyQt6 GUI thread.
    """

    frame_ready = pyqtSignal(np.ndarray, dict)
    snapshot_saved = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(self, output_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.output_dir = output_dir
        self._mutex = QMutex()
        self._running = False

        self._device_index: int = 0
        self._backend_name: str = "DirectShow"
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

        # Snapshot / Burst queue
        self._pending_snapshots: int = 0
        self._snapshot_format: str = "PNG Lossless"
        self._last_snapshot_time: float = 0.0
        self._snapshot_interval: float = 0.0

        # Watermark cache
        self._watermark_path: str = ""
        self._watermark_rgba: Optional[np.ndarray] = None

        # Sub-engines
        self.color_engine = ColorLUTEngine()
        self.ai_processor = AIProcessor()

        # Optional hooks for recorder & virtual camera
        self.recorder_hook = None
        self.virtual_cam_hook = None

    @staticmethod
    def enumerate_cameras(max_Check: int = 4) -> List[Tuple[int, str]]:
        """Probes camera indices and returns a list of (index, label)."""
        found: List[Tuple[int, str]] = []
        for idx in range(max_Check):
            cap = None
            try:
                if hasattr(cv2, "CAP_DSHOW"):
                    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(idx)
                if cap is not None and cap.isOpened():
                    label = f"USB Video Device #{idx} (C270 HD)" if idx == 0 else f"Capture Device #{idx}"
                    found.append((idx, label))
            except Exception:
                pass
            finally:
                if cap is not None:
                    cap.release()

        if not found:
            found.append((0, "Logitech HD Webcam C270 [Sim/UVC]"))
        return found

    def set_device(self, device_index: int, backend_name: str) -> None:
        with QMutexLocker(self._mutex):
            self._device_index = int(device_index)
            self._backend_name = str(backend_name)
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

    def trigger_snapshot(self, fmt: str = "PNG Lossless", count: int = 1, interval_sec: float = 0.18) -> None:
        with QMutexLocker(self._mutex):
            self._snapshot_format = fmt
            self._pending_snapshots += int(count)
            self._snapshot_interval = float(interval_sec)

    def stop_worker(self) -> None:
        with QMutexLocker(self._mutex):
            self._running = False
        self.wait(3000)

    def _open_capture(self, device_index: int, backend_name: str) -> Optional[cv2.VideoCapture]:
        api_pref = cv2.CAP_DSHOW if backend_name == "DirectShow" else cv2.CAP_MSMF
        try:
            cap = cv2.VideoCapture(device_index, api_pref)
            if not cap.isOpened():
                cap = cv2.VideoCapture(device_index)
            if cap.isOpened():
                # Stage 1: Configure MJPG 1280x720 @ 30 FPS
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return cap
        except Exception:
            pass
        return None

    def _sync_hardware_registers(self, cap: Optional[cv2.VideoCapture], params: Dict[str, Any]) -> None:
        """
        Applies Logitech C270 UVC DirectShow hardware registers when changed.
        Prevents the C270 driver from dropping shutter speed to 1/15s (15 FPS) in indoor lighting.
        """
        if cap is None or not cap.isOpened():
            return

        hw_sig = (
            bool(params.get("manual_exposure_lock", True)),
            bool(params.get("anti_flicker_50hz", True)),
            int(float(params.get("hardware_exposure", -5.0))),
            int(float(params.get("hardware_gain", 110.0))),
            int(float(params.get("backlight_comp", 0.0))),
            bool(params.get("auto_wb", True)),
            int(float(params.get("wb_kelvin", 5000.0))),
            int(float(params.get("hardware_brightness", 128.0))),
            int(float(params.get("hardware_contrast", 135.0))),
            int(float(params.get("hardware_saturation", 132.0))),
            int(float(params.get("hardware_sharpness", 140.0))),
        )
        if hw_sig == self._last_hw_signature:
            return
        self._last_hw_signature = hw_sig

        (
            manual_exp,
            flicker_50hz,
            exp_val,
            gain_val,
            backlight_val,
            auto_wb,
            wb_kelvin,
            bright,
            contrast,
            sat,
            sharp,
        ) = hw_sig

        try:
            if manual_exp:
                # DirectShow Manual Exposure mode = 0.25, MSMF = 1
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                cap.set(cv2.CAP_PROP_EXPOSURE, float(exp_val))
                cap.set(cv2.CAP_PROP_GAIN, float(gain_val))
            else:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)

            cap.set(cv2.CAP_PROP_BACKLIGHT, float(backlight_val))

            # Powerline frequency anti-flicker (1 = 50Hz, 2 = 60Hz on UVC drivers supporting property 39)
            CAP_PROP_POWERLINE = 39
            cap.set(CAP_PROP_POWERLINE, 1.0 if flicker_50hz else 2.0)

            if auto_wb:
                cap.set(cv2.CAP_PROP_AUTO_WB, 1.0)
            else:
                cap.set(cv2.CAP_PROP_AUTO_WB, 0.0)
                cap.set(cv2.CAP_PROP_WB_TEMPERATURE, float(wb_kelvin))

            cap.set(cv2.CAP_PROP_BRIGHTNESS, float(bright))
            cap.set(cv2.CAP_PROP_CONTRAST, float(contrast))
            cap.set(cv2.CAP_PROP_SATURATION, float(sat))
            cap.set(cv2.CAP_PROP_SHARPNESS, float(sharp))
        except Exception:
            pass

    @staticmethod
    def _generate_optical_reference_frame(tick: float) -> np.ndarray:
        """
        Generates a realistic 1280x720 studio portrait reference scene if no physical
        USB webcam is connected, allowing all ISP, LUT, AI segmentation, and PTZ stages
        to run on real pixel buffers.
        """
        h, w = 720, 1280
        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)

        # Studio background wall with subtle ambient lighting gradient
        bg_b = 38.0 + 18.0 * (1.0 - y_grid / h) + 12.0 * np.sin(x_grid / 220.0)
        bg_g = 36.0 + 16.0 * (1.0 - y_grid / h)
        bg_r = 40.0 + 14.0 * (x_grid / w)
        frame = np.stack([bg_b, bg_g, bg_r], axis=-1)

        # Warm practical key light in upper right background
        lx, ly = w * 0.76, h * 0.24
        ldist2 = ((x_grid - lx) / 220.0) ** 2 + ((y_grid - ly) / 180.0) ** 2
        glow = np.exp(-ldist2)
        frame[:, :, 2] += glow * 115.0
        frame[:, :, 1] += glow * 78.0
        frame[:, :, 0] += glow * 35.0

        # Subject subtle breathing / head motion
        cx = w * 0.50 + np.sin(tick * 0.9) * 18.0
        cy = h * 0.42 + np.cos(tick * 0.6) * 8.0

        # Shoulders / Jacket silhouette
        torso_dist = ((x_grid - cx) / 235.0) ** 2 + ((y_grid - (h * 0.88)) / 260.0) ** 2
        torso_mask = np.clip((1.0 - torso_dist) * 4.0, 0.0, 1.0)[:, :, None]
        jacket_color = np.array([28.0, 30.0, 34.0], dtype=np.float32)
        frame = frame * (1.0 - torso_mask) + jacket_color * torso_mask

        # Face oval with natural skin tones
        head_dist = ((x_grid - cx) / 96.0) ** 2 + ((y_grid - cy) / 126.0) ** 2
        head_mask = np.clip((1.0 - head_dist) * 6.0, 0.0, 1.0)
        key_shade = np.clip(0.85 + 0.22 * ((cx - x_grid) / 96.0), 0.65, 1.12)
        skin_b = 128.0 * key_shade
        skin_g = 158.0 * key_shade
        skin_r = 204.0 * key_shade
        skin_bgr = np.stack([skin_b, skin_g, skin_r], axis=-1)
        frame = frame * (1.0 - head_mask[:, :, None]) + skin_bgr * head_mask[:, :, None]

        # Color calibration patches in bottom-right of scene for LUT verification
        swatches_bgr = [
            (48, 58, 185),   # Crimson
            (60, 165, 225),  # Amber
            (85, 175, 75),   # Emerald
            (195, 135, 45),  # Cyan/Teal
            (180, 85, 145),  # Violet
            (215, 215, 215), # Neutral White
        ]
        for i, col in enumerate(swatches_bgr):
            sx0 = 80 + i * 34
            sy0 = 630
            frame[sy0 : sy0 + 24, sx0 : sx0 + 28] = col

        return np.clip(frame, 0, 255).astype(np.uint8)

    def _apply_ptz_and_geometry(
        self, frame_bgr: np.ndarray, params: Dict[str, Any], frame_idx: int
    ) -> Tuple[np.ndarray, Tuple[float, float, float]]:
        """
        Stage 2: Fluid Gimbal PTZ & AI Center Stage Auto-Framing + Mirror/Flip/Rotate.
        Returns (processed_frame, (cur_zoom, cur_pan_x, cur_pan_y)).
        """
        h, w = frame_bgr.shape[:2]

        # Mirror H / Flip V first so pan directions match viewer intuition
        if bool(params.get("mirror_h", True)):
            frame_bgr = cv2.flip(frame_bgr, 1)
        if bool(params.get("flip_v", False)):
            frame_bgr = cv2.flip(frame_bgr, 0)

        auto_framing = bool(params.get("auto_framing", False))
        damping = float(params.get("gimbal_damping", 0.08))

        if auto_framing:
            if frame_idx % 3 == 0:
                face_box = self.ai_processor.detect_face(frame_bgr)
                if face_box is not None:
                    fx_px, fy_px, fw_px, fh_px = face_box
                    self._auto_target_pan_x = float(np.clip(((fx_px + fw_px * 0.5) / w - 0.5) * 2.0, -1.0, 1.0))
                    self._auto_target_pan_y = float(np.clip(((fy_px + fh_px * 0.5) / h - 0.5) * 2.0, -1.0, 1.0))
            target_zoom = float(params.get("subject_target_zoom", 1.35))
            target_pan_x = self._auto_target_pan_x
            target_pan_y = self._auto_target_pan_y
        else:
            target_zoom = float(params.get("digital_zoom", 1.00))
            target_pan_x = float(params.get("pan_x", 0.00))
            target_pan_y = float(params.get("tilt_y", 0.00))

        # Exponential Moving Average (EMA) gimbal damping
        self.cur_zoom += (target_zoom - self.cur_zoom) * damping
        self.cur_pan_x += (target_pan_x - self.cur_pan_x) * damping
        self.cur_pan_y += (target_pan_y - self.cur_pan_y) * damping

        zoom = max(1.00, min(3.00, self.cur_zoom))
        if zoom > 1.002:
            crop_w = int(round(w / zoom))
            crop_h = int(round(h / zoom))
            max_dx = (w - crop_w) * 0.5
            max_dy = (h - crop_h) * 0.5
            cx = w * 0.5 + np.clip(self.cur_pan_x, -1.0, 1.0) * max_dx
            cy = h * 0.5 + np.clip(self.cur_pan_y, -1.0, 1.0) * max_dy

            x0 = int(np.clip(cx - crop_w * 0.5, 0, w - crop_w))
            y0 = int(np.clip(cy - crop_h * 0.5, 0, h - crop_h))
            cropped = frame_bgr[y0 : y0 + crop_h, x0 : x0 + crop_w]
            frame_bgr = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        rot_quad = int(params.get("rotate_quadrant", 0)) % 4
        if rot_quad == 1:
            frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)
            frame_bgr = cv2.resize(frame_bgr, (w, h), interpolation=cv2.INTER_LINEAR)
        elif rot_quad == 2:
            frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_180)
        elif rot_quad == 3:
            frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            frame_bgr = cv2.resize(frame_bgr, (w, h), interpolation=cv2.INTER_LINEAR)

        return frame_bgr, (zoom, self.cur_pan_x, self.cur_pan_y)

    @staticmethod
    def _apply_chroma_luma_denoise(frame_bgr: np.ndarray, strength: float) -> np.ndarray:
        """
        Stage 3: Low-Light Chroma/Luma Denoising.
        Converts BGR to YCrCb, blurs Cr/Cb channels to eliminate C270 sensor color speckles,
        and applies bilateral filtering on Luma Y.
        """
        if strength <= 0.01:
            return frame_bgr

        ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        cr_blur = cv2.GaussianBlur(cr, (5, 5), 0)
        cb_blur = cv2.GaussianBlur(cb, (5, 5), 0)
        cr_out = cv2.addWeighted(cr, 1.0 - strength, cr_blur, strength, 0)
        cb_out = cv2.addWeighted(cb, 1.0 - strength, cb_blur, strength, 0)

        sigma_color = max(5, int(35.0 * strength))
        y_out = cv2.bilateralFilter(y, d=5, sigmaColor=sigma_color, sigmaSpace=15)

        merged = cv2.merge([y_out, cr_out, cb_out])
        return cv2.cvtColor(merged, cv2.COLOR_YCrCb2BGR)

    @staticmethod
    def _apply_optical_clarity(frame_bgr: np.ndarray, clarity: float, detail_radius: float) -> np.ndarray:
        """Stage 7a: Optical Clarity via Unsharp Mask."""
        if clarity <= 0.01:
            return frame_bgr
        sigma = max(0.2, float(detail_radius))
        blur = cv2.GaussianBlur(frame_bgr, (0, 0), sigmaX=sigma)
        return cv2.addWeighted(frame_bgr, 1.0 + clarity, blur, -clarity, 0)

    def _burn_broadcast_overlays(
        self, frame_bgr: np.ndarray, params: Dict[str, Any], fps: float
    ) -> np.ndarray:
        """
        Stage 9: Broadcast Overlays burned into the output frame so Recording & Virtual Cam
        receive Lower Thirds, PNG Watermark, and Cinema Timecode.
        """
        h, w = frame_bgr.shape[:2]
        scale = w / 1280.0

        # 1. Lower Third Broadcast Graphic
        if bool(params.get("show_lower_third", False)):
            name_txt = str(params.get("lower_third_name", "ALEXANDER VANCE")).strip()
            role_txt = str(params.get("lower_third_role", "DIRECTOR OF PHOTOGRAPHY // LIVE")).strip()
            accent_choice = str(params.get("lower_third_accent", "Leica Amber (#E5A93C)"))

            if "Crimson" in accent_choice:
                accent_bgr = (72, 29, 225)  # #E11D48
            elif "Monochrome" in accent_choice:
                accent_bgr = (246, 244, 244)  # #F4F4F6
            else:
                accent_bgr = (60, 169, 229)  # #E5A93C

            x0 = int(48 * scale)
            card_h = int(68 * scale)
            y0 = h - int(56 * scale) - card_h
            card_w = int(max(340 * scale, min(w - x0 * 2, (max(len(name_txt), len(role_txt)) * 11 + 60) * scale)))

            x1 = min(w - 10, x0 + card_w)
            y1 = min(h - 10, y0 + card_h)

            if x1 > x0 and y1 > y0:
                roi = frame_bgr[y0:y1, x0:x1]
                dark_card = np.full_like(roi, (18, 14, 14), dtype=np.uint8)
                cv2.addWeighted(dark_card, 0.84, roi, 0.16, 0, dst=roi)
                # Border
                cv2.rectangle(frame_bgr, (x0, y0), (x1, y1), (48, 44, 44), 1)
                # 4px vertical accent bar
                bar_w = max(4, int(5 * scale))
                frame_bgr[y0:y1, x0 : x0 + bar_w] = accent_bgr

                # Typography
                cv2.putText(
                    frame_bgr,
                    name_txt[:42],
                    (x0 + bar_w + int(16 * scale), y0 + int(30 * scale)),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.68 * scale,
                    (246, 244, 244),
                    max(1, int(1.5 * scale)),
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    role_txt[:56],
                    (x0 + bar_w + int(16 * scale), y0 + int(52 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.46 * scale,
                    accent_bgr,
                    1,
                    cv2.LINE_AA,
                )

        # 2. Custom PNG Logo Watermark
        if bool(params.get("show_watermark", False)):
            wm_path = str(params.get("watermark_path", ""))
            if wm_path != self._watermark_path:
                self._watermark_path = wm_path
                self._watermark_rgba = None
                if wm_path and Path(wm_path).exists():
                    loaded = cv2.imread(wm_path, cv2.IMREAD_UNCHANGED)
                    if loaded is not None:
                        self._watermark_rgba = loaded

            if self._watermark_rgba is not None:
                wm = self._watermark_rgba
                target_w = int(140 * scale)
                wh_orig, ww_orig = wm.shape[:2]
                if ww_orig > 0 and wh_orig > 0:
                    target_h = max(16, int(wh_orig * (target_w / float(ww_orig))))
                    wm_resized = cv2.resize(wm, (target_w, target_h), interpolation=cv2.INTER_AREA)
                    pos = str(params.get("watermark_position", "Top-Right"))
                    pad = int(28 * scale)
                    if pos == "Top-Left":
                        wx, wy = pad, pad
                    elif pos == "Bottom-Right":
                        wx, wy = w - target_w - pad, h - target_h - pad
                    elif pos == "Bottom-Left":
                        wx, wy = pad, h - target_h - pad
                    else:
                        wx, wy = w - target_w - pad, pad

                    if wx >= 0 and wy >= 0 and wx + target_w <= w and wy + target_h <= h:
                        opacity = np.clip(float(params.get("watermark_opacity", 80.0)) / 100.0, 0.05, 1.0)
                        roi = frame_bgr[wy : wy + target_h, wx : wx + target_w]
                        if wm_resized.shape[2] == 4:
                            alpha = (wm_resized[:, :, 3:4].astype(np.float32) / 255.0) * opacity
                            bgr_wm = wm_resized[:, :, :3].astype(np.float32)
                        else:
                            alpha = opacity
                            bgr_wm = wm_resized[:, :, :3].astype(np.float32)
                        blended = roi.astype(np.float32) * (1.0 - alpha) + bgr_wm * alpha
                        frame_bgr[wy : wy + target_h, wx : wx + target_h if target_w == target_h else wx + target_w] = (
                            np.clip(blended, 0, 255).astype(np.uint8)
                        )

        # 3. Burn-in Cinema Timecode & Date
        if bool(params.get("burn_in_timecode", False)):
            now = datetime.now()
            ff = int((now.microsecond / 1_000_000.0) * max(1.0, fps))
            tc_str = now.strftime(f"%Y-%m-%d  %H:%M:%S:{ff:02d}")
            box_w = int(285 * scale)
            box_h = int(32 * scale)
            bx0 = w - box_w - int(28 * scale)
            by0 = h - box_h - int(24 * scale)
            bx1 = bx0 + box_w
            by1 = by0 + box_h
            roi = frame_bgr[by0:by1, bx0:bx1]
            dark_bg = np.full_like(roi, (12, 10, 10), dtype=np.uint8)
            cv2.addWeighted(dark_bg, 0.78, roi, 0.22, 0, dst=roi)
            cv2.rectangle(frame_bgr, (bx0, by0), (bx1, by1), (50, 48, 42), 1)
            cv2.putText(
                frame_bgr,
                tc_str,
                (bx0 + int(12 * scale), by0 + int(21 * scale)),
                cv2.FONT_HERSHEY_PLAIN,
                1.18 * scale,
                (60, 169, 229),
                max(1, int(1.4 * scale)),
                cv2.LINE_AA,
            )

        return frame_bgr

    def _save_snapshot_frame(self, frame_bgr: np.ndarray, fmt: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        if "JPG" in fmt.upper():
            out_path = self.output_dir / f"LEICA_C270_STILL_{ts}.jpg"
            cv2.imwrite(str(out_path), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 100])
        else:
            out_path = self.output_dir / f"LEICA_C270_STILL_{ts}.png"
            cv2.imwrite(str(out_path), frame_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        self.snapshot_saved.emit(str(out_path))
        self.status_message.emit(f"CAPTURED STILL -> {out_path.name}")

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
                    backend = self._backend_name
                    open_drv = self._open_driver_dialog_requested
                    self._reopen_requested = False
                    self._open_driver_dialog_requested = False
                    params = copy.deepcopy(self._params)

                if reopen:
                    if cap is not None:
                        cap.release()
                    cap = self._open_capture(dev_idx, backend)
                    self._last_hw_signature = None

                if open_drv and cap is not None and cap.isOpened():
                    try:
                        cap.set(cv2.CAP_PROP_SETTINGS, 1)
                    except Exception:
                        pass

                self._sync_hardware_registers(cap, params)

                # Stage 1: Capture Frame
                ret = False
                raw_frame = None
                if cap is not None and cap.isOpened():
                    ret, raw_frame = cap.read()

                if not ret or raw_frame is None:
                    raw_frame = self._generate_optical_reference_frame(time.perf_counter())
                    time.sleep(0.022)
                else:
                    if raw_frame.shape[1] != 1280 or raw_frame.shape[0] != 720:
                        raw_frame = cv2.resize(raw_frame, (1280, 720), interpolation=cv2.INTER_LINEAR)

                now_t = time.perf_counter()
                dt = max(1e-4, now_t - last_time)
                last_time = now_t
                fps_times.append(dt)
                avg_fps = len(fps_times) / sum(fps_times)

                frame_idx += 1

                # Stage 2: Fluid Gimbal PTZ & AI Auto-Framing
                frame, ptz_state = self._apply_ptz_and_geometry(raw_frame, params, frame_idx)

                # Stage 3: Low-Light Chroma/Luma Denoising
                denoise_val = float(params.get("denoise_strength", 0.15))
                frame = self._apply_chroma_luma_denoise(frame, denoise_val)

                # Stage 4: Dual-Engine AI Segmentation & Studio Lighting
                frame = self.ai_processor.process_studio_lighting(frame, params)

                # Stage 5: Frequency Portrait Skin Smoothing
                skin_val = float(params.get("skin_smoothing", 0.0))
                frame = self.ai_processor.apply_skin_smoothing(frame, skin_val)

                # Stage 6: Cinema Color Grading & 1D/3D LUT Engine
                frame = self.color_engine.apply_grade(frame, params)

                # Stage 7: Optical Clarity (Unsharp Mask), Vignette & Film Grain
                clarity_val = float(params.get("optical_clarity", 0.80))
                detail_rad = float(params.get("edge_detail_radius", 1.00))
                frame = self._apply_optical_clarity(frame, clarity_val, detail_rad)

                vignette_val = float(params.get("optical_vignette", 0.15))
                grain_val = float(params.get("film_grain", 0.00))
                frame = self.color_engine.apply_vignette_and_grain(frame, vignette_val, grain_val)

                # Stage 8: 1080p Lanczos4 Super-Sampling
                if bool(params.get("upscale_1080p", False)):
                    frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)

                # Stage 9: Broadcast Overlays
                frame = self._burn_broadcast_overlays(frame, params, avg_fps)

                # Stage 10: Real-Time 64-Bin Histogram Calculation
                hist_data = self.color_engine.compute_histogram_64(frame)

                # Handle Still / Burst Snapshots
                with QMutexLocker(self._mutex):
                    if self._pending_snapshots > 0 and (now_t - self._last_snapshot_time) >= self._snapshot_interval:
                        self._pending_snapshots -= 1
                        self._last_snapshot_time = now_t
                        snap_fmt = self._snapshot_format
                    else:
                        snap_fmt = ""

                if snap_fmt:
                    self._save_snapshot_frame(frame, snap_fmt)

                # Push to Recorder and Virtual Camera hooks if active
                if self.recorder_hook is not None and self.recorder_hook.is_recording:
                    self.recorder_hook.push_frame(frame)

                if self.virtual_cam_hook is not None and self.virtual_cam_hook.is_active:
                    self.virtual_cam_hook.send_frame(frame)

                out_h, out_w = frame.shape[:2]
                telemetry = {
                    "fps": avg_fps,
                    "width": out_w,
                    "height": out_h,
                    "upscaled": bool(params.get("upscale_1080p", False)),
                    "ptz": ptz_state,
                    "histogram": hist_data,
                    "ai_engine": self.ai_processor.engine_name,
                }
                self.frame_ready.emit(frame, telemetry)
        finally:
            if cap is not None:
                cap.release()
