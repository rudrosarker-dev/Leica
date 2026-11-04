# -*- coding: utf-8 -*-
"""
Clean Luminance-Weighted Color Grading & LUT Engine (`core/color_lut.py`).
Fixes dark-pixel red/green shadow posterization:
- All warmth, tint, and Studio Look channel shifts are weighted by `np.sin(L * np.pi)`
  so pure blacks (0) and pure whites (255) remain 100% neutral and never blotch red or green.
- Implements "Smart Light Boost (Dark Room Lift)" using a smooth floating-point shadow curve:
  `x = x ** (1.0 / (1.0 + boost * 0.8))`.
- Fast-path skip when all color/lighting parameters are at neutral defaults.
"""

from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np


STUDIO_LOOK_NAMES = [
    "Natural (Off)",
    "Warm Studio",
    "Clean Daylight",
    "Soft Portrait",
    "Cinema Teal",
    "Classic B&W",
]

# Legacy alias for backwards compatibility
FILM_LOOK_NAMES = STUDIO_LOOK_NAMES


class ColorLUTEngine:
    """High-speed, artifact-free 1D/Luminance-Weighted Color Engine."""

    def __init__(self) -> None:
        self._cached_sig: Optional[Tuple[Any, ...]] = None
        self._lut_256x3: np.ndarray = np.zeros((256, 1, 3), dtype=np.uint8)
        self._is_identity: bool = True
        self._vignette_cache: Dict[Tuple[int, int, float], np.ndarray] = {}
        self._build_identity_lut()

    def _build_identity_lut(self) -> None:
        ramp = np.arange(256, dtype=np.uint8).reshape((256, 1, 1))
        self._lut_256x3 = np.repeat(ramp, 3, axis=2)
        self._is_identity = True

    @staticmethod
    def is_color_and_light_neutral(params: Dict[str, Any]) -> bool:
        """Returns True if all lighting and color parameters are at their neutral 0 defaults."""
        if bool(params.get("pure_view_bypass", False)):
            return True
        return (
            abs(float(params.get("light_boost", 0.0))) < 0.1
            and abs(float(params.get("brightness", 0.0))) < 0.1
            and abs(float(params.get("contrast", 0.0))) < 0.1
            and str(params.get("active_lut", "Natural (Off)")) == "Natural (Off)"
            and abs(float(params.get("warmth", 0.0))) < 0.1
            and abs(float(params.get("tint", 0.0))) < 0.1
            and abs(float(params.get("saturation", 0.0))) < 0.1
            and abs(float(params.get("vignette", 0.0))) < 0.1
        )

    @staticmethod
    def _apply_studio_look_curves(
        x: np.ndarray, mid_bell: np.ndarray, look_name: str
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes clean R, G, B curves in [0.0, 1.0] for the selected Studio Look.
        Uses `mid_bell = np.sin(x * np.pi)` so dark shadows (x=0) and highlights (x=1)
        never suffer raw channel clipping or red/green color corruption.
        """
        if look_name == "Warm Studio":
            # Gentle golden midtone warmth + smooth shadow lift
            lifted = np.power(x, 0.94)
            r = np.clip(lifted + 0.038 * mid_bell, 0.0, 1.0)
            g = np.clip(lifted + 0.012 * mid_bell, 0.0, 1.0)
            b = np.clip(lifted - 0.032 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name == "Clean Daylight":
            # Crisp neutral-cool daylight balance with clean white clarity
            base = np.clip(x * 0.96 + 0.04 * (x ** 0.88), 0.0, 1.0)
            r = np.clip(base - 0.014 * mid_bell, 0.0, 1.0)
            g = np.clip(base + 0.006 * mid_bell, 0.0, 1.0)
            b = np.clip(base + 0.028 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name == "Soft Portrait":
            # Silky midtone lift and gentle contrast roll-off for flattering skin tones
            soft = np.power(x, 0.92)
            soft = soft - 0.025 * np.sin((soft - 0.5) * np.pi)
            r = np.clip(soft + 0.024 * mid_bell, 0.0, 1.0)
            g = np.clip(soft + 0.008 * mid_bell, 0.0, 1.0)
            b = np.clip(soft - 0.016 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name == "Cinema Teal":
            # Smooth luminance-weighted teal lower-midtones and warm upper-midtones
            # Zero offset at x=0 and x=1 thanks to mid_bell envelope!
            low_mid = mid_bell * (1.0 - x)
            high_mid = mid_bell * x
            r = np.clip(x - 0.035 * low_mid + 0.048 * high_mid, 0.0, 1.0)
            g = np.clip(x + 0.018 * low_mid + 0.012 * high_mid, 0.0, 1.0)
            b = np.clip(x + 0.045 * low_mid - 0.038 * high_mid, 0.0, 1.0)
            return r, g, b

        if look_name in ("Classic B&W", "Classic B&&W"):
            # Fine-art silver monochrome tone curve
            sig = 1.0 / (1.0 + np.exp(-5.2 * (x - 0.5)))
            s0 = 1.0 / (1.0 + np.exp(-5.2 * -0.5))
            s1 = 1.0 / (1.0 + np.exp(-5.2 * 0.5))
            mono = np.clip((sig - s0) / (s1 - s0), 0.0, 1.0)
            return mono, mono.copy(), mono.copy()

        # Default: Natural (Off)
        return x.copy(), x.copy(), x.copy()

    def _ensure_lut_updated(self, params: Dict[str, Any]) -> None:
        sig = (
            round(float(params.get("light_boost", 0.0)), 1),
            round(float(params.get("brightness", 0.0)), 1),
            round(float(params.get("contrast", 0.0)), 1),
            str(params.get("active_lut", "Natural (Off)")),
            round(float(params.get("look_intensity", 75.0)), 1),
            round(float(params.get("warmth", 0.0)), 1),
            round(float(params.get("tint", 0.0)), 1),
        )
        if sig == self._cached_sig:
            return
        self._cached_sig = sig

        (
            light_boost_pct,
            brightness_val,
            contrast_val,
            active_lut,
            look_intensity_pct,
            warmth_val,
            tint_val,
        ) = sig

        if (
            abs(light_boost_pct) < 0.1
            and abs(brightness_val) < 0.1
            and abs(contrast_val) < 0.1
            and active_lut == "Natural (Off)"
            and abs(warmth_val) < 0.1
            and abs(tint_val) < 0.1
        ):
            self._build_identity_lut()
            return

        self._is_identity = False
        x = np.linspace(0.0, 1.0, 256, dtype=np.float32)

        # 1. Smart Room Light Boost (Shadow Lift): x = x ** (1.0 / (1.0 + boost * 0.8))
        boost = np.clip(light_boost_pct / 100.0, 0.0, 1.0)
        if boost > 0.001:
            x = np.power(x, 1.0 / (1.0 + boost * 0.8))

        # 2. Brightness (smooth midtone-weighted lift so black floor doesn't wash out)
        if abs(brightness_val) > 0.1:
            b_norm = brightness_val / 100.0
            x = np.clip(x + b_norm * 0.28 * np.sin(x * np.pi * 0.85 + 0.15), 0.0, 1.0)

        # 3. Contrast (smooth centered S-curve / slope around 0.5)
        if abs(contrast_val) > 0.1:
            c_norm = contrast_val / 100.0
            if c_norm > 0:
                k = 3.5 + c_norm * 5.0
                sig = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
                s0 = 1.0 / (1.0 + np.exp(-k * -0.5))
                s1 = 1.0 / (1.0 + np.exp(-k * 0.5))
                sig_norm = (sig - s0) / (s1 - s0)
                x = (1.0 - c_norm * 0.65) * x + (c_norm * 0.65) * sig_norm
            else:
                x = np.clip(0.5 + (x - 0.5) * (1.0 + c_norm * 0.45), 0.0, 1.0)

        # 4. Luminance-Weighted Warmth & Tint: shift * np.sin(L * np.pi)
        # Guarantees pure blacks (0) and pure whites (1) NEVER tint red or green!
        mid_bell = np.sin(x * np.pi)
        w_norm = warmth_val / 100.0
        t_norm = tint_val / 100.0

        r = np.clip(x + (w_norm * 0.11 + t_norm * 0.03) * mid_bell, 0.0, 1.0)
        g = np.clip(x + (-t_norm * 0.09) * mid_bell, 0.0, 1.0)
        b = np.clip(x + (-w_norm * 0.11 + t_norm * 0.03) * mid_bell, 0.0, 1.0)

        # 5. Studio Look Transfer Curve blended by Look Intensity
        mix = np.clip(look_intensity_pct / 100.0, 0.0, 1.0)
        if active_lut != "Natural (Off)" and mix > 0.001:
            r_look, g_look, b_look = self._apply_studio_look_curves(r, np.sin(r * np.pi), active_lut)
            _, g_look_g, _ = self._apply_studio_look_curves(g, np.sin(g * np.pi), active_lut)
            _, _, b_look_b = self._apply_studio_look_curves(b, np.sin(b * np.pi), active_lut)
            r = np.clip((1.0 - mix) * r + mix * r_look, 0.0, 1.0)
            g = np.clip((1.0 - mix) * g + mix * g_look_g, 0.0, 1.0)
            b = np.clip((1.0 - mix) * b + mix * b_look_b, 0.0, 1.0)

        bgr_table = np.zeros((256, 1, 3), dtype=np.uint8)
        bgr_table[:, 0, 0] = np.clip(b * 255.0, 0.0, 255.0).astype(np.uint8)
        bgr_table[:, 0, 1] = np.clip(g * 255.0, 0.0, 255.0).astype(np.uint8)
        bgr_table[:, 0, 2] = np.clip(r * 255.0, 0.0, 255.0).astype(np.uint8)
        self._lut_256x3 = bgr_table

    def apply_grade(self, frame_bgr: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Applies fast 1D LUT, Classic B&W monochrome blend, saturation, and soft vignette."""
        if self.is_color_and_light_neutral(params):
            return frame_bgr

        self._ensure_lut_updated(params)
        out = frame_bgr if self._is_identity else cv2.LUT(frame_bgr, self._lut_256x3)

        active_lut = str(params.get("active_lut", "Natural (Off)"))
        look_mix = np.clip(float(params.get("look_intensity", 75.0)) / 100.0, 0.0, 1.0)

        if active_lut in ("Classic B&W", "Classic B&&W") and look_mix > 0.01:
            gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
            mono_bgr = cv2.merge([gray, gray, gray])
            out = mono_bgr if look_mix >= 0.99 else cv2.addWeighted(out, 1.0 - look_mix, mono_bgr, look_mix, 0.0)
        else:
            sat = float(params.get("saturation", 0.0))
            if abs(sat) > 0.5:
                hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
                s = hsv[:, :, 1]
                weight = 1.0 - (s / 255.0) * 0.5
                hsv[:, :, 1] = np.clip(s + (sat / 100.0) * 95.0 * weight, 0.0, 255.0)
                out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        vig_pct = float(params.get("vignette", 0.0))
        if vig_pct > 0.5:
            out = self.apply_soft_vignette(out, vig_pct / 100.0)

        return out

    def apply_soft_vignette(self, frame_bgr: np.ndarray, strength: float) -> np.ndarray:
        if strength <= 0.005:
            return frame_bgr
        h, w = frame_bgr.shape[:2]
        key = (w, h, round(strength, 2))
        if key not in self._vignette_cache:
            y_grid, x_grid = np.ogrid[:h, :w]
            nx = (x_grid - w * 0.5) / (w * 0.5)
            ny = (y_grid - h * 0.5) / (h * 0.5)
            r2 = nx * nx + ny * ny
            falloff = np.clip(1.0 - strength * 0.48 * (r2 ** 1.25), 0.25, 1.0).astype(np.float32)
            self._vignette_cache[key] = falloff[:, :, None]
            if len(self._vignette_cache) > 8:
                self._vignette_cache.pop(next(iter(self._vignette_cache)))
        return np.clip(frame_bgr.astype(np.float32) * self._vignette_cache[key], 0.0, 255.0).astype(np.uint8)

    @staticmethod
    def compute_histogram_64(frame_bgr: np.ndarray) -> Dict[str, np.ndarray]:
        small = frame_bgr[::4, ::4]
        b_hist = cv2.calcHist([small], [0], None, [64], [0, 256]).flatten()
        g_hist = cv2.calcHist([small], [1], None, [64], [0, 256]).flatten()
        r_hist = cv2.calcHist([small], [2], None, [64], [0, 256]).flatten()
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        y_hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten()

        def _norm(arr: np.ndarray) -> np.ndarray:
            peak = float(np.max(arr))
            return np.zeros(64, dtype=np.float32) if peak <= 1e-5 else np.clip(arr / peak, 0.0, 1.0).astype(np.float32)

        return {"r": _norm(r_hist), "g": _norm(g_hist), "b": _norm(b_hist), "luma": _norm(y_hist)}
