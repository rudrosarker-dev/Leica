# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — AI Portrait Studio Segmentation, Skin Softening & Face Center Stage (`core/ai_processor.py`).
Supports:
- Background Modes: Off (Natural), Optical Bokeh Blur, Studio Dimmed Spotlight, Custom Backdrop
- Portrait Skin Softening (0% to 100%)
- AI Face Auto-Framing (Center Stage)
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
    """Zero-overhead-when-off AI Portrait Background, Skin Retouch & Auto-Frame Processor."""

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

        cascade_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        self._smooth_face_box: Tuple[float, float, float, float] = (0.36, 0.24, 0.28, 0.42)
        self._frame_counter: int = 0
        self._backdrop_cache_path: str = ""
        self._backdrop_cache_img: Optional[np.ndarray] = None

    def detect_face(self, frame_bgr: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        h, w = frame_bgr.shape[:2]
        if self._face_cascade.empty():
            return None

        small_w = 320
        scale = small_w / float(w)
        small_h = max(180, int(h * scale))
        gray = cv2.cvtColor(cv2.resize(frame_bgr, (small_w, small_h)), cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(32, 32))
        if len(faces) == 0:
            return None

        fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
        px, py, pw, ph = int(fx / scale), int(fy / scale), int(fw / scale), int(fh / scale)

        nx, ny, nw, nh = px / float(w), py / float(h), pw / float(w), ph / float(h)
        sx, sy, sw, sh = self._smooth_face_box
        alpha = 0.22
        self._smooth_face_box = (
            sx + (nx - sx) * alpha,
            sy + (ny - sy) * alpha,
            sw + (nw - sw) * alpha,
            sh + (nh - sh) * alpha,
        )
        return (px, py, pw, ph)

    def _compute_fallback_elliptical_mask(self, h: int, w: int) -> np.ndarray:
        fx, fy, fw, fh = self._smooth_face_box
        cx = (fx + fw * 0.5) * w
        head_cy = (fy + fh * 0.52) * h
        head_rx = max(w * 0.13, fw * w * 0.78)
        head_ry = max(h * 0.21, fh * h * 0.92)

        torso_cy = min(h * 0.95, head_cy + head_ry * 1.45)
        torso_rx = head_rx * 1.85
        torso_ry = head_ry * 1.55

        gh, gw = max(45, h // 4), max(80, w // 4)
        y_grid, x_grid = np.ogrid[:gh, :gw]
        x_px = x_grid * (w / float(gw))
        y_px = y_grid * (h / float(gh))

        head_dist2 = ((x_px - cx) / head_rx) ** 2 + ((y_px - head_cy) / head_ry) ** 2
        torso_dist2 = ((x_px - cx) / torso_rx) ** 2 + ((y_px - torso_cy) / torso_ry) ** 2

        combined = np.maximum(np.exp(-(head_dist2 ** 1.65)), np.exp(-(torso_dist2 ** 1.55))).astype(np.float32)
        combined = np.clip((combined - 0.15) / 0.72, 0.0, 1.0)
        return cv2.resize(combined, (w, h), interpolation=cv2.INTER_LINEAR)

    def compute_subject_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
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

        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        return np.clip(mask, 0.0, 1.0)

    def apply_skin_softening(self, frame_bgr: np.ndarray, skin_pct: float) -> np.ndarray:
        """Applies frequency-preserving bilateral portrait skin smoothing on YCrCb skin-tone regions."""
        if skin_pct <= 1.0:
            return frame_bgr
        strength = float(np.clip(skin_pct / 100.0, 0.0, 1.0))
        ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
        skin_mask = cv2.inRange(ycrcb, (35, 132, 77), (250, 175, 128))
        skin_mask = cv2.GaussianBlur(skin_mask, (9, 9), 0).astype(np.float32) / 255.0
        alpha = (skin_mask * strength * 0.72)[:, :, None]

        small = cv2.resize(frame_bgr, (frame_bgr.shape[1] // 2, frame_bgr.shape[0] // 2))
        smooth_small = cv2.bilateralFilter(small, d=5, sigmaColor=36, sigmaSpace=14)
        smooth_full = cv2.resize(smooth_small, (frame_bgr.shape[1], frame_bgr.shape[0]))
        blended = frame_bgr.astype(np.float32) * (1.0 - alpha) + smooth_full.astype(np.float32) * alpha
        return np.clip(blended, 0.0, 255.0).astype(np.uint8)

    def _get_custom_backdrop(self, w: int, h: int, backdrop_path: str) -> np.ndarray:
        if backdrop_path and backdrop_path != self._backdrop_cache_path:
            p = Path(backdrop_path)
            if p.exists():
                img = cv2.imread(str(p), cv2.IMREAD_COLOR)
                if img is not None:
                    self._backdrop_cache_img = img
                    self._backdrop_cache_path = backdrop_path
        if self._backdrop_cache_img is not None:
            return cv2.resize(self._backdrop_cache_img, (w, h), interpolation=cv2.INTER_LINEAR)

        # Architectural dark slate studio backdrop fallback
        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w * 0.5, h * 0.42
        r2 = ((x_grid - cx) / (w * 0.55)) ** 2 + ((y_grid - cy) / (h * 0.55)) ** 2
        glow = np.exp(-r2)
        b = 26.0 + 34.0 * glow
        g = 24.0 + 30.0 * glow
        r = 22.0 + 28.0 * glow
        return np.clip(np.stack([b, g, r], axis=-1), 0, 255).astype(np.uint8)

    def process_background(self, frame_bgr: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        Fast-path skip when bg_mode is Off and skin_softening is 0.
        """
        if bool(params.get("pure_view_bypass", False)):
            return frame_bgr

        skin_pct = float(params.get("skin_softening", 0.0))
        if skin_pct > 1.0:
            frame_bgr = self.apply_skin_softening(frame_bgr, skin_pct)

        mode = str(params.get("bg_mode", "Off (Natural)"))
        if mode.startswith("Off"):
            return frame_bgr

        h, w = frame_bgr.shape[:2]
        strength = float(np.clip(float(params.get("bg_strength", 50.0)) / 100.0, 0.10, 1.0))
        mask_3d = self.compute_subject_mask(frame_bgr)[:, :, None]

        if mode in ("Optical Bokeh Blur", "Portrait Bokeh Blur", "Soft Bokeh Blur"):
            small_bg = cv2.resize(frame_bgr, (w // 2, h // 2), interpolation=cv2.INTER_LINEAR)
            k = max(3, int(round(strength * 30.0)) | 1)
            blurred_small = cv2.GaussianBlur(small_bg, (k, k), 0)
            bg_blur = cv2.resize(blurred_small, (w, h), interpolation=cv2.INTER_LINEAR)
            comp = frame_bgr.astype(np.float32) * mask_3d + bg_blur.astype(np.float32) * (1.0 - mask_3d)
            return np.clip(comp, 0.0, 255.0).astype(np.uint8)

        if mode in ("Studio Dimmed Spotlight", "Studio Dimmed Background (Spotlight)", "Subtle Studio Spotlight"):
            dim_mult = 1.0 - (strength * 0.78)
            bg = frame_bgr.astype(np.float32) * dim_mult
            comp = frame_bgr.astype(np.float32) * mask_3d + bg * (1.0 - mask_3d)
            return np.clip(comp, 0.0, 255.0).astype(np.uint8)

        if mode == "Custom Backdrop":
            backdrop = self._get_custom_backdrop(w, h, str(params.get("custom_backdrop_path", "")))
            comp = frame_bgr.astype(np.float32) * mask_3d + backdrop.astype(np.float32) * (1.0 - mask_3d)
            return np.clip(comp, 0.0, 255.0).astype(np.uint8)

        return frame_bgr
