# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — Luminance-Weighted Color Grading & .CUBE 3D LUT Engine (`core/color_lut.py`).
Supports all 8 Cinema Film Looks:
1. Pure Natural (Off)
2. Warm Studio
3. Clean Daylight
4. Kodak Portra
5. Cinema Teal/Amber
6. Soft Peach Skin
7. Matte Obsidian
8. Leica B&W
Plus custom .CUBE 1D/3D LUT file loading and zero-latency shadow lift for 30-FPS Anti-Lag Boost.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np


STUDIO_LOOK_NAMES = [
    "Pure Natural (Off)",
    "Warm Studio",
    "Clean Daylight",
    "Kodak Portra",
    "Cinema Teal/Amber",
    "Soft Peach Skin",
    "Matte Obsidian",
    "Leica B&W",
]

FILM_LOOK_NAMES = STUDIO_LOOK_NAMES


class ColorLUTEngine:
    """High-speed, artifact-free 1D/Luminance-Weighted & .CUBE Color Grading Engine."""

    def __init__(self) -> None:
        self._cached_sig: Optional[Tuple[Any, ...]] = None
        self._lut_256x3: np.ndarray = np.zeros((256, 1, 3), dtype=np.uint8)
        self._is_identity: bool = True
        self._vignette_cache: Dict[Tuple[int, int, float], np.ndarray] = {}
        self._custom_cube_lut: Optional[np.ndarray] = None
        self._custom_cube_path: str = ""
        self._build_identity_lut()

    def _build_identity_lut(self) -> None:
        ramp = np.arange(256, dtype=np.uint8).reshape((256, 1, 1))
        self._lut_256x3 = np.repeat(ramp, 3, axis=2)
        self._is_identity = True

    def load_cube_file(self, file_path: str) -> bool:
        """Parses standard Adobe/Resolve .CUBE LUT files into a fast 256x1x3 lookup table."""
        path = Path(file_path)
        if not path.exists():
            return False
        try:
            rows = []
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or line.startswith("TITLE") or line.startswith("DOMAIN"):
                        continue
                    if line.startswith("LUT_"):
                        continue
                    parts = line.split()
                    if len(parts) == 3:
                        try:
                            r_f, g_f, b_f = float(parts[0]), float(parts[1]), float(parts[2])
                            rows.append((r_f, g_f, b_f))
                        except ValueError:
                            continue
            if not rows:
                return False

            arr = np.array(rows, dtype=np.float32)
            n = len(arr)
            # If 3D LUT (e.g. 17^3 or 33^3), extract the neutral diagonal for 1D fast curve
            cube_root = int(round(n ** (1.0 / 3.0)))
            if abs(cube_root ** 3 - n) <= 2 and cube_root >= 8:
                diag_indices = [
                    i + i * cube_root + i * (cube_root * cube_root)
                    for i in range(cube_root)
                ]
                diag = arr[diag_indices]
            else:
                diag = arr

            src_x = np.linspace(0.0, 1.0, len(diag), dtype=np.float32)
            dst_x = np.linspace(0.0, 1.0, 256, dtype=np.float32)
            r_curve = np.interp(dst_x, src_x, diag[:, 0])
            g_curve = np.interp(dst_x, src_x, diag[:, 1])
            b_curve = np.interp(dst_x, src_x, diag[:, 2])

            lut = np.zeros((256, 1, 3), dtype=np.uint8)
            lut[:, 0, 0] = np.clip(b_curve * 255.0, 0.0, 255.0).astype(np.uint8)
            lut[:, 0, 1] = np.clip(g_curve * 255.0, 0.0, 255.0).astype(np.uint8)
            lut[:, 0, 2] = np.clip(r_curve * 255.0, 0.0, 255.0).astype(np.uint8)
            self._custom_cube_lut = lut
            self._custom_cube_path = str(path)
            self._cached_sig = None
            return True
        except Exception:
            return False

    @staticmethod
    def is_color_and_light_neutral(params: Dict[str, Any]) -> bool:
        """Returns True if all lighting and color parameters are at their neutral 0 defaults."""
        if bool(params.get("pure_view_bypass", False)):
            return True
        active_lut = str(params.get("active_lut", "Pure Natural (Off)"))
        return (
            abs(float(params.get("light_boost", 0.0))) < 0.1
            and abs(float(params.get("brightness", 0.0))) < 0.1
            and abs(float(params.get("contrast", 0.0))) < 0.1
            and active_lut in ("Pure Natural (Off)", "Natural (Off)")
            and not str(params.get("custom_cube_path", "")).strip()
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
        Computes clean R, G, B curves in [0.0, 1.0] for the 8 Cinema Film Looks.
        Uses `mid_bell = np.sin(x * np.pi)` so dark shadows (x=0) and highlights (x=1)
        never suffer raw channel clipping or red/green color corruption.
        """
        if look_name == "Warm Studio":
            lifted = np.power(x, 0.93)
            r = np.clip(lifted + 0.042 * mid_bell, 0.0, 1.0)
            g = np.clip(lifted + 0.014 * mid_bell, 0.0, 1.0)
            b = np.clip(lifted - 0.034 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name == "Clean Daylight":
            base = np.clip(x * 0.96 + 0.04 * (x ** 0.88), 0.0, 1.0)
            r = np.clip(base - 0.012 * mid_bell, 0.0, 1.0)
            g = np.clip(base + 0.008 * mid_bell, 0.0, 1.0)
            b = np.clip(base + 0.028 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name == "Kodak Portra":
            # Golden analog film warmth with gentle highlight roll-off and rich midtones
            film = np.power(x, 0.91)
            film = film - 0.02 * np.sin((film - 0.5) * np.pi)
            r = np.clip(film + 0.046 * mid_bell, 0.0, 1.0)
            g = np.clip(film + 0.018 * mid_bell, 0.0, 1.0)
            b = np.clip(film - 0.028 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name in ("Cinema Teal/Amber", "Cinema Teal"):
            low_mid = mid_bell * (1.0 - x)
            high_mid = mid_bell * x
            r = np.clip(x - 0.038 * low_mid + 0.054 * high_mid, 0.0, 1.0)
            g = np.clip(x + 0.018 * low_mid + 0.014 * high_mid, 0.0, 1.0)
            b = np.clip(x + 0.048 * low_mid - 0.042 * high_mid, 0.0, 1.0)
            return r, g, b

        if look_name in ("Soft Peach Skin", "Soft Portrait"):
            soft = np.power(x, 0.92)
            soft = soft - 0.025 * np.sin((soft - 0.5) * np.pi)
            r = np.clip(soft + 0.032 * mid_bell, 0.0, 1.0)
            g = np.clip(soft + 0.012 * mid_bell, 0.0, 1.0)
            b = np.clip(soft - 0.014 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name == "Matte Obsidian":
            # Cinematic lifted matte shadow floor with controlled speculars
            matte = 0.04 * mid_bell + np.power(x, 0.96) * 0.96
            sig = 1.0 / (1.0 + np.exp(-4.2 * (matte - 0.5)))
            s0 = 1.0 / (1.0 + np.exp(-4.2 * -0.5))
            s1 = 1.0 / (1.0 + np.exp(-4.2 * 0.5))
            norm = np.clip((sig - s0) / (s1 - s0), 0.0, 1.0)
            r = np.clip(norm + 0.015 * mid_bell, 0.0, 1.0)
            g = np.clip(norm + 0.005 * mid_bell, 0.0, 1.0)
            b = np.clip(norm - 0.010 * mid_bell, 0.0, 1.0)
            return r, g, b

        if look_name in ("Leica B&W", "Classic B&W", "Classic B&&W"):
            sig = 1.0 / (1.0 + np.exp(-5.4 * (x - 0.5)))
            s0 = 1.0 / (1.0 + np.exp(-5.4 * -0.5))
            s1 = 1.0 / (1.0 + np.exp(-5.4 * 0.5))
            mono = np.clip((sig - s0) / (s1 - s0), 0.0, 1.0)
            return mono, mono.copy(), mono.copy()

        return x.copy(), x.copy(), x.copy()

    def _ensure_lut_updated(self, params: Dict[str, Any]) -> None:
        cube_path = str(params.get("custom_cube_path", "")).strip()
        if cube_path and cube_path != self._custom_cube_path:
            self.load_cube_file(cube_path)
        elif not cube_path:
            self._custom_cube_lut = None
            self._custom_cube_path = ""

        sig = (
            round(float(params.get("light_boost", 0.0)), 1),
            round(float(params.get("brightness", 0.0)), 1),
            round(float(params.get("contrast", 0.0)), 1),
            str(params.get("active_lut", "Pure Natural (Off)")),
            round(float(params.get("look_intensity", 75.0)), 1),
            round(float(params.get("warmth", 0.0)), 1),
            round(float(params.get("tint", 0.0)), 1),
            self._custom_cube_path,
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
            _,
        ) = sig

        if (
            abs(light_boost_pct) < 0.1
            and abs(brightness_val) < 0.1
            and abs(contrast_val) < 0.1
            and active_lut in ("Pure Natural (Off)", "Natural (Off)")
            and self._custom_cube_lut is None
            and abs(warmth_val) < 0.1
            and abs(tint_val) < 0.1
        ):
            self._build_identity_lut()
            return

        self._is_identity = False
        x = np.linspace(0.0, 1.0, 256, dtype=np.float32)

        # 1. Smart Room Light Boost (Zero-Latency Shadow Lift for 30-FPS Anti-Lag Boost)
        boost = np.clip(light_boost_pct / 100.0, 0.0, 1.0)
        if boost > 0.001:
            x = np.power(x, 1.0 / (1.0 + boost * 0.85))

        # 2. Digital Brightness (midtone-weighted lift so black floor doesn't wash out)
        if abs(brightness_val) > 0.1:
            b_norm = brightness_val / 100.0
            x = np.clip(x + b_norm * 0.28 * np.sin(x * np.pi * 0.85 + 0.15), 0.0, 1.0)

        # 3. Micro-Contrast (centered S-curve around 0.5)
        if abs(contrast_val) > 0.1:
            c_norm = contrast_val / 100.0
            if c_norm > 0:
                k = 3.5 + c_norm * 5.0
                sig_c = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
                s0 = 1.0 / (1.0 + np.exp(-k * -0.5))
                s1 = 1.0 / (1.0 + np.exp(-k * 0.5))
                sig_norm = (sig_c - s0) / (s1 - s0)
                x = (1.0 - c_norm * 0.65) * x + (c_norm * 0.65) * sig_norm
            else:
                x = np.clip(0.5 + (x - 0.5) * (1.0 + c_norm * 0.45), 0.0, 1.0)

        # 4. Luminance-Weighted Warmth & Tint
        mid_bell = np.sin(x * np.pi)
        w_norm = warmth_val / 100.0
        t_norm = tint_val / 100.0

        r = np.clip(x + (w_norm * 0.11 + t_norm * 0.03) * mid_bell, 0.0, 1.0)
        g = np.clip(x + (-t_norm * 0.09) * mid_bell, 0.0, 1.0)
        b = np.clip(x + (-w_norm * 0.11 + t_norm * 0.03) * mid_bell, 0.0, 1.0)

        # 5. Cinema Film Look Transfer Curve blended by Look Intensity
        mix = np.clip(look_intensity_pct / 100.0, 0.0, 1.0)
        if active_lut not in ("Pure Natural (Off)", "Natural (Off)") and mix > 0.001:
            r_look, _, _ = self._apply_studio_look_curves(r, np.sin(r * np.pi), active_lut)
            _, g_look, _ = self._apply_studio_look_curves(g, np.sin(g * np.pi), active_lut)
            _, _, b_look = self._apply_studio_look_curves(b, np.sin(b * np.pi), active_lut)
            r = np.clip((1.0 - mix) * r + mix * r_look, 0.0, 1.0)
            g = np.clip((1.0 - mix) * g + mix * g_look, 0.0, 1.0)
            b = np.clip((1.0 - mix) * b + mix * b_look, 0.0, 1.0)

        bgr_table = np.zeros((256, 1, 3), dtype=np.uint8)
        bgr_table[:, 0, 0] = np.clip(b * 255.0, 0.0, 255.0).astype(np.uint8)
        bgr_table[:, 0, 1] = np.clip(g * 255.0, 0.0, 255.0).astype(np.uint8)
        bgr_table[:, 0, 2] = np.clip(r * 255.0, 0.0, 255.0).astype(np.uint8)

        if self._custom_cube_lut is not None and mix > 0.001:
            bgr_table = cv2.addWeighted(
                bgr_table, 1.0 - mix, self._custom_cube_lut, mix, 0.0
            )

        self._lut_256x3 = bgr_table

    def apply_grade(self, frame_bgr: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Applies fast 1D LUT, Leica B&W monochrome blend, HSV vibrance, and optical lens vignette."""
        if self.is_color_and_light_neutral(params):
            return frame_bgr

        self._ensure_lut_updated(params)
        out = frame_bgr if self._is_identity else cv2.LUT(frame_bgr, self._lut_256x3)

        active_lut = str(params.get("active_lut", "Pure Natural (Off)"))
        look_mix = np.clip(float(params.get("look_intensity", 75.0)) / 100.0, 0.0, 1.0)

        if active_lut in ("Leica B&W", "Classic B&W", "Classic B&&W") and look_mix > 0.01:
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
            falloff = np.clip(1.0 - strength * 0.48 * (r2 ** 1.25), 0.22, 1.0).astype(np.float32)
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
