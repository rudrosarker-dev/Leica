# -*- coding: utf-8 -*-
"""
Dual-Engine AI Segmentation, Studio Spotlight, Optical Bokeh, Custom Backdrop,
AI Center Stage Auto-Framing, and Frequency Portrait Skin Smoothing (`core/ai_processor.py`).

Resilience Law:
- Primary segmentation engine uses MediaPipe SelfieSegmentation if installed.
- Mandatory Fallback Engine uses OpenCV Haar Cascade Face Detector + Face-Anchored
  Elliptical Radial Mask so Studio Spotlight, Optical Bokeh, Custom Backdrop, and
  AI Center Stage Auto-Framing work 100% across Python 3.10–3.14 even without MediaPipe.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np

try:
    import mediapipe as mp  # type: ignore

    HAS_MEDIAPIPE = hasattr(mp, "solutions") and hasattr(mp.solutions, "selfie_segmentation")
except Exception:
    mp = None
    HAS_MEDIAPIPE = False


class AIProcessor:
    """Dual-Engine AI Subject Segmentation, Face Gimbal Tracker, and Skin Retouch Processor."""

    def __init__(self) -> None:
        self.mediapipe_active = False
        self._segmenter = None
        if HAS_MEDIAPIPE:
            try:
                self._segmenter = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
                self.mediapipe_active = True
            except Exception:
                self._segmenter = None
                self.mediapipe_active = False

        # Load OpenCV built-in Haar Cascade face detector for Auto-Framing & Fallback Masking
        cascade_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        self._face_cascade = cv2.CascadeClassifier(cascade_path)

        # Smoothed face bounding box state (x, y, w, h) in normalized [0..1] coordinates
        self._smooth_face_box: Tuple[float, float, float, float] = (0.36, 0.24, 0.28, 0.42)
        self._has_recent_face: bool = False
        self._frame_counter: int = 0

        # Cached backdrop image
        self._backdrop_path: str = ""
        self._backdrop_img_raw: Optional[np.ndarray] = None
        self._backdrop_resized_cache: Dict[Tuple[int, int], np.ndarray] = {}

    @property
    def engine_name(self) -> str:
        return "MediaPipe Neural Seg" if self.mediapipe_active else "OpenCV Optical Radial Seg"

    def detect_face(self, frame_bgr: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detects the primary subject's face bounding box (x, y, w, h) in pixel coordinates.
        Updates internal smoothed normalized coordinates for stable mask/gimbal tracking.
        """
        h, w = frame_bgr.shape[:2]
        if self._face_cascade.empty():
            return None

        small_w = 320
        scale = small_w / float(w)
        small_h = max(180, int(h * scale))
        gray = cv2.cvtColor(cv2.resize(frame_bgr, (small_w, small_h)), cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=4,
            minSize=(32, 32),
        )
        if len(faces) == 0:
            return None

        # Choose largest face
        fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
        px = int(fx / scale)
        py = int(fy / scale)
        pw = int(fw / scale)
        ph = int(fh / scale)

        # Update smoothed normalized box with EMA
        nx, ny, nw, nh = px / float(w), py / float(h), pw / float(w), ph / float(h)
        sx, sy, sw, sh = self._smooth_face_box
        alpha = 0.25
        self._smooth_face_box = (
            sx + (nx - sx) * alpha,
            sy + (ny - sy) * alpha,
            sw + (nw - sw) * alpha,
            sh + (nh - sh) * alpha,
        )
        self._has_recent_face = True
        return (px, py, pw, ph)

    def _compute_fallback_elliptical_mask(self, h: int, w: int) -> np.ndarray:
        """
        Computes a smooth dual-ellipse radial subject mask (head + shoulders/torso)
        anchored to the detected face center so Spotlight, Bokeh, and Backdrop work 100%
        without MediaPipe.
        """
        fx, fy, fw, fh = self._smooth_face_box
        cx = (fx + fw * 0.5) * w
        head_cy = (fy + fh * 0.52) * h
        head_rx = max(w * 0.13, fw * w * 0.78)
        head_ry = max(h * 0.21, fh * h * 0.92)

        torso_cy = min(h * 0.95, head_cy + head_ry * 1.45)
        torso_rx = head_rx * 1.85
        torso_ry = head_ry * 1.55

        # Compute on 1/4 resolution grid for ultra-fast vector math
        gh, gw = max(45, h // 4), max(80, w // 4)
        y_grid, x_grid = np.ogrid[:gh, :gw]
        sx = w / float(gw)
        sy = h / float(gh)

        x_px = x_grid * sx
        y_px = y_grid * sy

        head_dist2 = ((x_px - cx) / head_rx) ** 2 + ((y_px - head_cy) / head_ry) ** 2
        torso_dist2 = ((x_px - cx) / torso_rx) ** 2 + ((y_px - torso_cy) / torso_ry) ** 2

        head_mask = np.exp(- (head_dist2 ** 1.65))
        torso_mask = np.exp(- (torso_dist2 ** 1.55))
        combined = np.maximum(head_mask, torso_mask).astype(np.float32)
        combined = np.clip((combined - 0.15) / 0.72, 0.0, 1.0)

        return cv2.resize(combined, (w, h), interpolation=cv2.INTER_LINEAR)

    def compute_subject_mask(self, frame_bgr: np.ndarray, feather: int) -> np.ndarray:
        """Returns a float32 mask in [0.0, 1.0] of shape (H, W)."""
        h, w = frame_bgr.shape[:2]
        self._frame_counter += 1

        mask: Optional[np.ndarray] = None
        if self.mediapipe_active and self._segmenter is not None:
            try:
                rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                res = self._segmenter.process(rgb)
                if res is not None and res.segmentation_mask is not None:
                    mask = np.clip(res.segmentation_mask.astype(np.float32), 0.0, 1.0)
            except Exception:
                self.mediapipe_active = False
                mask = None

        if mask is None:
            if self._frame_counter % 4 == 0:
                self.detect_face(frame_bgr)
            mask = self._compute_fallback_elliptical_mask(h, w)

        k = max(1, int(feather)) * 2 + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
        return np.clip(mask, 0.0, 1.0)

    def _get_backdrop_frame(self, h: int, w: int, color_hex: str, image_path: str) -> np.ndarray:
        """Returns a (H, W, 3) uint8 BGR backdrop from custom image or studio swatch hex."""
        if image_path != self._backdrop_path:
            self._backdrop_path = image_path
            self._backdrop_img_raw = None
            self._backdrop_resized_cache.clear()
            if image_path and Path(image_path).exists():
                loaded = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if loaded is not None:
                    self._backdrop_img_raw = loaded

        if self._backdrop_img_raw is not None:
            key = (w, h)
            if key not in self._backdrop_resized_cache:
                self._backdrop_resized_cache[key] = cv2.resize(
                    self._backdrop_img_raw, (w, h), interpolation=cv2.INTER_LINEAR
                )
            return self._backdrop_resized_cache[key]

        hex_clean = color_hex.lstrip("#")
        if len(hex_clean) == 6:
            try:
                r = int(hex_clean[0:2], 16)
                g = int(hex_clean[2:4], 16)
                b = int(hex_clean[4:6], 16)
            except ValueError:
                r, g, b = 18, 18, 22
        else:
            r, g, b = 18, 18, 22

        bg = np.empty((h, w, 3), dtype=np.uint8)
        bg[:, :, 0] = b
        bg[:, :, 1] = g
        bg[:, :, 2] = r
        return bg

    def process_studio_lighting(self, frame_bgr: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        Executes Stage 4: Studio Spotlight, Optical Bokeh Blur, or Custom Studio Backdrop.
        """
        mode = str(params.get("ai_mode", "Studio Spotlight (Dim Background)"))
        if mode == "Off (Natural Scene)":
            return frame_bgr

        h, w = frame_bgr.shape[:2]
        feather = int(float(params.get("edge_feather", 7.0)))
        mask = self.compute_subject_mask(frame_bgr, feather)
        mask_3d = mask[:, :, None]

        if mode == "Studio Spotlight (Dim Background)":
            dim_pct = np.clip(float(params.get("spotlight_dim_pct", 45.0)) / 100.0, 0.0, 0.95)
            bg = frame_bgr.astype(np.float32) * (1.0 - dim_pct)
            # Subtle cool ambient separation: Blue * 1.06, Red * 0.94
            bg[:, :, 0] = np.clip(bg[:, :, 0] * 1.06, 0.0, 255.0)
            bg[:, :, 2] = np.clip(bg[:, :, 2] * 0.94, 0.0, 255.0)
            comp = frame_bgr.astype(np.float32) * mask_3d + bg * (1.0 - mask_3d)
            return np.clip(comp, 0.0, 255.0).astype(np.uint8)

        if mode == "Optical Bokeh Blur (DSLR Portrait)":
            radius = int(float(params.get("bokeh_blur_radius", 25.0)))
            blur_k = max(3, radius | 1)
            # Downsample 2x before heavy blur for 60FPS responsiveness, then upsample
            small_bg = cv2.resize(frame_bgr, (w // 2, h // 2), interpolation=cv2.INTER_LINEAR)
            k_half = max(3, (blur_k // 2) | 1)
            blurred_small = cv2.GaussianBlur(small_bg, (k_half, k_half), 0)
            bg_blur = cv2.resize(blurred_small, (w, h), interpolation=cv2.INTER_LINEAR)
            comp = frame_bgr.astype(np.float32) * mask_3d + bg_blur.astype(np.float32) * (1.0 - mask_3d)
            return np.clip(comp, 0.0, 255.0).astype(np.uint8)

        if mode == "Custom Studio Backdrop":
            color_hex = str(params.get("backdrop_color_hex", "#121216"))
            img_path = str(params.get("backdrop_image_path", ""))
            bg = self._get_backdrop_frame(h, w, color_hex, img_path)
            comp = frame_bgr.astype(np.float32) * mask_3d + bg.astype(np.float32) * (1.0 - mask_3d)
            return np.clip(comp, 0.0, 255.0).astype(np.uint8)

        return frame_bgr

    @staticmethod
    def apply_skin_smoothing(frame_bgr: np.ndarray, skin_smooth: float) -> np.ndarray:
        """
        Executes Stage 5: Frequency Portrait Skin Smoothing.
        Builds HSV skin-tone mask (0, 25, 50) to (28, 175, 255), feathers with 5x5 Gaussian,
        and blends bilateral-filtered frame by skin_smooth * 0.75 while keeping eyes/brows crisp.
        """
        if skin_smooth <= 0.01:
            return frame_bgr

        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        skin_mask = cv2.inRange(
            hsv,
            np.array([0, 25, 50], dtype=np.uint8),
            np.array([28, 175, 255], dtype=np.uint8),
        )
        skin_mask_f = cv2.GaussianBlur(skin_mask, (5, 5), 0).astype(np.float32) / 255.0
        smoothed = cv2.bilateralFilter(frame_bgr, d=7, sigmaColor=40, sigmaSpace=40)

        alpha = (skin_mask_f * float(skin_smooth) * 0.75)[:, :, None]
        blended = frame_bgr.astype(np.float32) * (1.0 - alpha) + smoothed.astype(np.float32) * alpha
        return np.clip(blended, 0.0, 255.0).astype(np.uint8)
