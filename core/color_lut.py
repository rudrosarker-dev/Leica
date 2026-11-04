# -*- coding: utf-8 -*-
"""
Cinema Color Grading & 1D/3D LUT Mathematical Engine (`core/color_lut.py`).
Implements:
- Pre-computed 256x3 uint8 1D Lookup Table for primary grading + 6 Film Looks
- Custom .CUBE 3D LUT parser & trilinear interpolation engine
- HSV Smart Vibrance (boosts muted tones while protecting skin saturation)
- Software Kelvin White Balance RGB matrix compensation
- Real-Time 64-Bin RGB + Luminance Histogram calculator
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np


FILM_LOOK_NAMES = [
    "Rec.709 Neutral",
    "Kodak Portra 400",
    "Leica Monochrome",
    "Teal & Orange",
    "Matte Obsidian",
    "Warm Tungsten",
]


class ColorLUTEngine:
    """High-speed NumPy/OpenCV LUT Color Grading Engine."""

    def __init__(self) -> None:
        self._cached_signature: Optional[Tuple[Any, ...]] = None
        self._lut_256x3: np.ndarray = np.zeros((256, 1, 3), dtype=np.uint8)
        self._custom_cube_path: str = ""
        self._custom_cube_lut: Optional[np.ndarray] = None
        self._custom_cube_size: int = 0
        self._vignette_cache: Dict[Tuple[int, int, float], np.ndarray] = {}
        self._grain_buffer: np.ndarray = np.random.normal(0.0, 1.0, (1120, 1980)).astype(np.float32)
        self._build_default_identity_lut()

    def _build_default_identity_lut(self) -> None:
        ramp = np.arange(256, dtype=np.uint8).reshape((256, 1, 1))
        self._lut_256x3 = np.repeat(ramp, 3, axis=2)

    def load_cube_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Parses an Adobe/Iridas .cube 1D or 3D LUT file.
        Returns (success, status_message).
        """
        if not file_path:
            self._custom_cube_path = ""
            self._custom_cube_lut = None
            self._custom_cube_size = 0
            self._cached_signature = None
            return True, "Cleared custom LUT"

        path = Path(file_path)
        if not path.exists():
            return False, f"LUT file not found: {path.name}"

        try:
            size_3d = 0
            size_1d = 0
            data_rows = []
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    upper = line.upper()
                    if upper.startswith("TITLE") or upper.startswith("DOMAIN_"):
                        continue
                    if upper.startswith("LUT_3D_SIZE"):
                        parts = line.split()
                        if len(parts) >= 2:
                            size_3d = int(parts[1])
                        continue
                    if upper.startswith("LUT_1D_SIZE"):
                        parts = line.split()
                        if len(parts) >= 2:
                            size_1d = int(parts[1])
                        continue
                    parts = line.split()
                    if len(parts) == 3:
                        try:
                            r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                            data_rows.append((r, g, b))
                        except ValueError:
                            continue

            arr = np.array(data_rows, dtype=np.float32)
            if size_3d > 1 and arr.shape[0] == size_3d ** 3:
                # .cube files iterate Red fastest, then Green, then Blue
                lut_3d = arr.reshape((size_3d, size_3d, size_3d, 3))
                self._custom_cube_lut = np.clip(lut_3d, 0.0, 1.0)
                self._custom_cube_size = size_3d
                self._custom_cube_path = str(path)
                self._cached_signature = None
                return True, f"Loaded 3D LUT ({size_3d}x{size_3d}x{size_3d}): {path.name}"
            elif size_1d > 1 and arr.shape[0] == size_1d:
                # Resample 1D LUT onto 256 grid
                x_src = np.linspace(0.0, 1.0, size_1d, dtype=np.float32)
                x_dst = np.linspace(0.0, 1.0, 256, dtype=np.float32)
                r_1d = np.interp(x_dst, x_src, arr[:, 0])
                g_1d = np.interp(x_dst, x_src, arr[:, 1])
                b_1d = np.interp(x_dst, x_src, arr[:, 2])
                lut_1d = np.stack([r_1d, g_1d, b_1d], axis=-1)
                self._custom_cube_lut = np.clip(lut_1d, 0.0, 1.0)
                self._custom_cube_size = -256  # Sentinel for 1D custom LUT
                self._custom_cube_path = str(path)
                self._cached_signature = None
                return True, f"Loaded 1D LUT ({size_1d}): {path.name}"
            else:
                return False, f"Invalid .cube dimensions ({arr.shape[0]} rows)"
        except Exception as exc:
            return False, f"Failed to parse .cube: {exc}"

    @staticmethod
    def _apply_film_look_curves(
        r: np.ndarray, g: np.ndarray, b: np.ndarray, film_look: str
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Applies exact mathematical transfer curves for the 6 studio film looks.
        Inputs r, g, b are float32 arrays in range [0.0, 1.0].
        """
        if film_look == "Kodak Portra 400":
            # Lifted warm shadows (R+6, G+3, B-4 in 0..255), golden midtones, soft 0.96 highlight shoulder
            r_out = np.clip((r ** 0.94) * 0.94 + (6.0 / 255.0) * (1.0 - r) + 0.015 * np.sin(r * np.pi), 0.0, 0.96)
            g_out = np.clip((g ** 0.97) * 0.95 + (3.0 / 255.0) * (1.0 - g) + 0.008 * np.sin(g * np.pi), 0.0, 0.96)
            b_out = np.clip((b ** 1.04) * 0.96 - (4.0 / 255.0) * (1.0 - b), 0.0, 0.95)
            return r_out, g_out, b_out

        if film_look == "Leica Monochrome":
            # High-acutance silver-halide B&W (L = 0.25*R + 0.65*G + 0.10*B) with steep S-curve & 8-level floor
            luma = 0.25 * r + 0.65 * g + 0.10 * b
            sig = 1.0 / (1.0 + np.exp(-7.2 * (luma - 0.48)))
            sig_min = 1.0 / (1.0 + np.exp(-7.2 * (0.0 - 0.48)))
            sig_max = 1.0 / (1.0 + np.exp(-7.2 * (1.0 - 0.48)))
            sig_norm = (sig - sig_min) / (sig_max - sig_min)
            floor = 8.0 / 255.0
            mono = np.clip(floor + (1.0 - floor) * sig_norm, 0.0, 1.0)
            return mono, mono.copy(), mono.copy()

        if film_look == "Teal & Orange":
            # Shadow luminances (<0.5) shifted toward cyan/teal (B+14, G+6, R-10),
            # Mid/high luminances shifted toward warm amber (R+12, G+4, B-10)
            shadow_weight = np.clip(1.0 - r * 1.8, 0.0, 1.0)
            high_weight = np.clip((r - 0.35) * 1.5, 0.0, 1.0)
            r_out = np.clip(r + (-10.0 / 255.0) * shadow_weight + (12.0 / 255.0) * high_weight, 0.0, 1.0)
            g_out = np.clip(g + (6.0 / 255.0) * shadow_weight + (4.0 / 255.0) * high_weight, 0.0, 1.0)
            b_out = np.clip(b + (14.0 / 255.0) * shadow_weight + (-10.0 / 255.0) * high_weight, 0.0, 1.0)
            return r_out, g_out, b_out

        if film_look == "Matte Obsidian":
            # Deep crushed mid-shadows with lifted #141416 matte black floor: x = 0.06 + 0.88 * (x ** 1.15)
            r_out = np.clip(0.06 + 0.88 * (r ** 1.16), 0.0, 0.95)
            g_out = np.clip(0.06 + 0.87 * (g ** 1.18), 0.0, 0.94)
            b_out = np.clip(0.068 + 0.89 * (b ** 1.14), 0.0, 0.96)
            return r_out, g_out, b_out

        if film_look == "Warm Tungsten":
            # Rich 3200K studio warmth (R+14, G+5, B-16) with silky highlight compression
            r_out = np.clip((r ** 0.92) + (14.0 / 255.0) * (1.0 - 0.5 * r), 0.0, 0.98)
            g_out = np.clip((g ** 0.97) + (5.0 / 255.0) * (1.0 - 0.5 * g), 0.0, 0.98)
            b_out = np.clip((b ** 1.08) - (16.0 / 255.0) * (1.0 - 0.3 * b), 0.0, 0.96)
            return r_out, g_out, b_out

        # Default: Rec.709 Neutral
        return r, g, b

    def _ensure_lut_updated(self, params: Dict[str, Any]) -> None:
        signature = (
            params.get("film_look", "Kodak Portra 400"),
            round(float(params.get("lut_intensity", 100.0)), 2),
            round(float(params.get("temp_shift", 0.0)), 2),
            round(float(params.get("tint_shift", 0.0)), 2),
            round(float(params.get("shadows_lift", 0.0)), 2),
            round(float(params.get("midtones_gamma", 1.0)), 3),
            round(float(params.get("highlights_gain", 0.0)), 2),
            round(float(params.get("scurve_contrast", 0.15)), 3),
            bool(params.get("auto_wb", True)),
            round(float(params.get("wb_kelvin", 5000.0)), 0),
            self._custom_cube_path,
        )
        if signature == self._cached_signature:
            return
        self._cached_signature = signature

        x = np.linspace(0.0, 1.0, 256, dtype=np.float32)

        lift = float(params.get("shadows_lift", 0.0))
        gamma = max(0.20, float(params.get("midtones_gamma", 1.00)))
        gain = float(params.get("highlights_gain", 0.0))
        contrast = float(params.get("scurve_contrast", 0.15))
        temp = float(params.get("temp_shift", 0.0))
        tint = float(params.get("tint_shift", 0.0))
        lut_mix = np.clip(float(params.get("lut_intensity", 100.0)) / 100.0, 0.0, 1.0)
        film_look = str(params.get("film_look", "Kodak Portra 400"))

        # 1. Shadow Lift, Midtone Gamma, Highlight Gain
        base = np.clip(x * (1.0 + gain / 100.0 - lift / 100.0) + lift / 100.0, 0.0, 1.0)
        base = np.power(base, 1.0 / gamma)

        # 2. S-Curve Contrast
        if contrast > 0.001:
            k = 4.0 + contrast * 8.0
            sig = 1.0 / (1.0 + np.exp(-k * (base - 0.5)))
            sig_0 = 1.0 / (1.0 + np.exp(-k * (-0.5)))
            sig_1 = 1.0 / (1.0 + np.exp(-k * (0.5)))
            sig_norm = (sig - sig_0) / (sig_1 - sig_0)
            base = (1.0 - contrast) * base + contrast * sig_norm

        # 3. Color Temp & Tint channel offsets + Manual Kelvin fine shift
        kelvin_shift = 0.0
        if not bool(params.get("auto_wb", True)):
            kelvin_val = float(params.get("wb_kelvin", 5000.0))
            kelvin_shift = (kelvin_val - 5000.0) / 65.0

        r_offset = (temp * 0.4 + kelvin_shift * 0.35) / 255.0
        b_offset = (-temp * 0.4 - kelvin_shift * 0.35) / 255.0
        g_offset = (-tint * 0.35) / 255.0

        r = np.clip(base + r_offset, 0.0, 1.0)
        g = np.clip(base + g_offset, 0.0, 1.0)
        b = np.clip(base + b_offset, 0.0, 1.0)

        # 4. Film Look Mathematical Transfer Function (or 1D .cube)
        if self._custom_cube_lut is not None and self._custom_cube_size == -256:
            idx_r = np.clip((r * 255.0).astype(np.int32), 0, 255)
            idx_g = np.clip((g * 255.0).astype(np.int32), 0, 255)
            idx_b = np.clip((b * 255.0).astype(np.int32), 0, 255)
            r_look = self._custom_cube_lut[idx_r, 0]
            g_look = self._custom_cube_lut[idx_g, 1]
            b_look = self._custom_cube_lut[idx_b, 2]
        else:
            r_look, g_look, b_look = self._apply_film_look_curves(r, g, b, film_look)

        r_final = np.clip((1.0 - lut_mix) * r + lut_mix * r_look, 0.0, 1.0)
        g_final = np.clip((1.0 - lut_mix) * g + lut_mix * g_look, 0.0, 1.0)
        b_final = np.clip((1.0 - lut_mix) * b + lut_mix * b_look, 0.0, 1.0)

        # OpenCV uses BGR ordering
        bgr_table = np.zeros((256, 1, 3), dtype=np.uint8)
        bgr_table[:, 0, 0] = np.clip(b_final * 255.0, 0.0, 255.0).astype(np.uint8)
        bgr_table[:, 0, 1] = np.clip(g_final * 255.0, 0.0, 255.0).astype(np.uint8)
        bgr_table[:, 0, 2] = np.clip(r_final * 255.0, 0.0, 255.0).astype(np.uint8)
        self._lut_256x3 = bgr_table

    def _apply_3d_cube_lut(self, frame_bgr: np.ndarray, intensity: float) -> np.ndarray:
        """Applies loaded 3D .cube LUT via fast lattice lookup."""
        if self._custom_cube_lut is None or self._custom_cube_size <= 1:
            return frame_bgr

        n = self._custom_cube_size
        scale = float(n - 1) / 255.0
        b_idx = np.clip((frame_bgr[:, :, 0].astype(np.float32) * scale).round().astype(np.int32), 0, n - 1)
        g_idx = np.clip((frame_bgr[:, :, 1].astype(np.float32) * scale).round().astype(np.int32), 0, n - 1)
        r_idx = np.clip((frame_bgr[:, :, 2].astype(np.float32) * scale).round().astype(np.int32), 0, n - 1)

        mapped_rgb = self._custom_cube_lut[b_idx, g_idx, r_idx] * 255.0
        mapped_bgr = mapped_rgb[:, :, ::-1].astype(np.uint8)
        if intensity >= 0.999:
            return mapped_bgr
        return cv2.addWeighted(frame_bgr, 1.0 - intensity, mapped_bgr, intensity, 0.0)

    def apply_grade(self, frame_bgr: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Applies 1D/3D LUT, Leica Monochrome desaturation, and Smart Vibrance."""
        custom_path = str(params.get("custom_cube_path", ""))
        if custom_path != self._custom_cube_path:
            self.load_cube_file(custom_path)

        self._ensure_lut_updated(params)

        graded = cv2.LUT(frame_bgr, self._lut_256x3)

        lut_mix = np.clip(float(params.get("lut_intensity", 100.0)) / 100.0, 0.0, 1.0)
        if self._custom_cube_lut is not None and self._custom_cube_size > 1 and lut_mix > 0.0:
            graded = self._apply_3d_cube_lut(graded, lut_mix)

        # If Leica Monochrome is selected, blend saturation down according to lut_mix
        if params.get("film_look") == "Leica Monochrome" and lut_mix > 0.0:
            b_ch = graded[:, :, 0].astype(np.float32)
            g_ch = graded[:, :, 1].astype(np.float32)
            r_ch = graded[:, :, 2].astype(np.float32)
            mono = (0.10 * b_ch + 0.65 * g_ch + 0.25 * r_ch).astype(np.uint8)
            mono_bgr = cv2.merge([mono, mono, mono])
            if lut_mix >= 0.99:
                graded = mono_bgr
            else:
                graded = cv2.addWeighted(graded, 1.0 - lut_mix, mono_bgr, lut_mix, 0.0)

        # Smart Vibrance in HSV space
        vibrance = float(params.get("vibrance", 15.0))
        if abs(vibrance) > 0.5 and params.get("film_look") != "Leica Monochrome":
            hsv = cv2.cvtColor(graded, cv2.COLOR_BGR2HSV).astype(np.float32)
            s = hsv[:, :, 1]
            # Weight: less-saturated pixels receive stronger boost without clipping skin tones
            weight = 1.0 - (s / 255.0)
            s_Delta = (vibrance / 100.0) * 115.0 * weight
            hsv[:, :, 1] = np.clip(s + s_Delta, 0.0, 255.0)
            graded = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        return graded

    def apply_vignette_and_grain(
        self, frame_bgr: np.ndarray, vignette_strength: float, grain_strength: float
    ) -> np.ndarray:
        """Applies cached 2D radial cosine-fourth optical vignette and organic luma grain."""
        h, w = frame_bgr.shape[:2]
        out = frame_bgr

        if vignette_strength > 0.005:
            key = (w, h, round(vignette_strength, 2))
            if key not in self._vignette_cache:
                y_grid, x_grid = np.ogrid[:h, :w]
                nx = (x_grid - w * 0.5) / (w * 0.5)
                ny = (y_grid - h * 0.5) / (h * 0.5)
                r2 = nx * nx + ny * ny
                # Cosine-fourth optical falloff approximation
                falloff = np.clip(1.0 - vignette_strength * 0.58 * (r2 ** 1.15), 0.12, 1.0).astype(np.float32)
                self._vignette_cache[key] = falloff[:, :, None]
                if len(self._vignette_cache) > 12:
                    self._vignette_cache.pop(next(iter(self._vignette_cache)))

            mask = self._vignette_cache[key]
            out = np.clip(out.astype(np.float32) * mask, 0.0, 255.0).astype(np.uint8)

        if grain_strength > 0.005:
            bh, bw = self._grain_buffer.shape
            if h < bh - 20 and w < bw - 20:
                oy = np.random.randint(0, bh - h)
                ox = np.random.randint(0, bw - w)
                noise_slice = self._grain_buffer[oy : oy + h, ox : ox + w] * (grain_strength * 18.0)
                noisy = out.astype(np.float32) + noise_slice[:, :, None]
                out = np.clip(noisy, 0.0, 255.0).astype(np.uint8)

        return out

    @staticmethod
    def compute_histogram_64(frame_bgr: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Downsamples frame 4x for speed, computes 64-bin histograms for R, G, B, and Luma,
        and normalizes each curve to [0.0, 1.0].
        """
        small = frame_bgr[::4, ::4]
        b_hist = cv2.calcHist([small], [0], None, [64], [0, 256]).flatten()
        g_hist = cv2.calcHist([small], [1], None, [64], [0, 256]).flatten()
        r_hist = cv2.calcHist([small], [2], None, [64], [0, 256]).flatten()
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        y_hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten()

        def _norm(arr: np.ndarray) -> np.ndarray:
            peak = float(np.max(arr))
            if peak <= 1e-5:
                return np.zeros(64, dtype=np.float32)
            return np.clip(arr / peak, 0.0, 1.0).astype(np.float32)

        return {
            "r": _norm(r_hist),
            "g": _norm(g_hist),
            "b": _norm(b_hist),
            "luma": _norm(y_hist),
        }
