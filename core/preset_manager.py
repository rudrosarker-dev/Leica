# -*- coding: utf-8 -*-
"""
Preset Management System & Factory Calibration Profiles for Logitech C270 HD Webcam.
Stores and loads JSON configurations in ~/Pictures/C270_Optix_Studio/presets.json.
"""

import copy
import json
from pathlib import Path
from typing import Dict, Any, List


DEFAULT_STUDIO_PARAMS: Dict[str, Any] = {
    # Zone B - Card 1: C270 30-FPS Hardware Engine
    "manual_exposure_lock": True,
    "anti_flicker_50hz": True,
    "hardware_exposure": -5.0,
    "hardware_gain": 110.0,
    "backlight_comp": 0.0,

    # Zone B - Card 2: Sensor Color & White Balance
    "auto_wb": True,
    "wb_kelvin": 5000.0,
    "hardware_brightness": 128.0,
    "hardware_contrast": 135.0,
    "hardware_saturation": 132.0,
    "hardware_sharpness": 140.0,

    # Zone B - Card 3: Optical ISP & Super-Resolution
    "upscale_1080p": False,
    "optical_clarity": 0.80,
    "denoise_strength": 0.15,
    "edge_detail_radius": 1.00,

    # Zone B - Card 4: Fluid PTZ & Geometry
    "digital_zoom": 1.00,
    "pan_x": 0.00,
    "tilt_y": 0.00,
    "mirror_h": True,
    "flip_v": False,
    "rotate_quadrant": 0,

    # Zone D - Tab 1: Color & LUT
    "film_look": "Kodak Portra 400",
    "custom_cube_path": "",
    "lut_intensity": 100.0,
    "temp_shift": 0.0,
    "tint_shift": 0.0,
    "shadows_lift": 0.0,
    "midtones_gamma": 1.00,
    "highlights_gain": 0.0,
    "scurve_contrast": 0.15,
    "vibrance": 15.0,
    "optical_vignette": 0.15,
    "film_grain": 0.00,

    # Zone D - Tab 2: AI Studio
    "ai_mode": "Studio Spotlight (Dim Background)",
    "spotlight_dim_pct": 45.0,
    "bokeh_blur_radius": 25.0,
    "edge_feather": 7.0,
    "backdrop_color_hex": "#121216",
    "backdrop_image_path": "",
    "auto_framing": False,
    "subject_target_zoom": 1.35,
    "gimbal_damping": 0.08,
    "skin_smoothing": 0.00,

    # Zone D - Tab 3: Overlays
    "show_histogram": True,
    "show_vu_meter": True,
    "guide_thirds": False,
    "guide_golden": False,
    "guide_crosshair_safe": False,
    "guide_anamorphic": False,
    "guide_vertical_reel": False,
    "show_lower_third": False,
    "lower_third_name": "ALEXANDER VANCE",
    "lower_third_role": "DIRECTOR OF PHOTOGRAPHY // LIVE",
    "lower_third_accent": "Leica Amber (#E5A93C)",
    "show_watermark": False,
    "watermark_path": "",
    "watermark_position": "Top-Right",
    "watermark_opacity": 80.0,
    "burn_in_timecode": False,
}


FACTORY_PRESETS: Dict[str, Dict[str, Any]] = {
    "1. C270 30FPS Low-Light Fix": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "manual_exposure_lock": True,
        "anti_flicker_50hz": True,
        "hardware_exposure": -5.0,
        "hardware_gain": 115.0,
        "backlight_comp": 0.0,
        "auto_wb": False,
        "wb_kelvin": 4800.0,
        "denoise_strength": 0.30,
        "optical_clarity": 0.90,
        "film_look": "Rec.709 Neutral",
        "lut_intensity": 100.0,
        "shadows_lift": 4.0,
        "midtones_gamma": 1.08,
        "highlights_gain": -4.0,
        "scurve_contrast": 0.18,
        "vibrance": 14.0,
        "ai_mode": "Studio Spotlight (Dim Background)",
        "spotlight_dim_pct": 40.0,
    },
    "2. Warm Aesthetic Portrait": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "manual_exposure_lock": True,
        "hardware_exposure": -5.0,
        "hardware_gain": 105.0,
        "auto_wb": False,
        "wb_kelvin": 5300.0,
        "optical_clarity": 0.65,
        "denoise_strength": 0.20,
        "film_look": "Kodak Portra 400",
        "lut_intensity": 92.0,
        "temp_shift": 12.0,
        "tint_shift": 4.0,
        "shadows_lift": 3.0,
        "midtones_gamma": 1.04,
        "highlights_gain": -6.0,
        "scurve_contrast": 0.20,
        "vibrance": 18.0,
        "optical_vignette": 0.22,
        "film_grain": 0.08,
        "ai_mode": "Optical Bokeh Blur (DSLR Portrait)",
        "bokeh_blur_radius": 31.0,
        "skin_smoothing": 0.30,
    },
    "3. Crisp 1080p Broadcast": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "manual_exposure_lock": True,
        "hardware_exposure": -5.0,
        "hardware_gain": 100.0,
        "upscale_1080p": True,
        "optical_clarity": 1.15,
        "denoise_strength": 0.15,
        "edge_detail_radius": 0.90,
        "film_look": "Teal & Orange",
        "lut_intensity": 75.0,
        "scurve_contrast": 0.22,
        "vibrance": 20.0,
        "optical_vignette": 0.12,
        "ai_mode": "Studio Spotlight (Dim Background)",
        "spotlight_dim_pct": 50.0,
        "show_lower_third": True,
    },
    "4. Leica Monochrome Studio": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "manual_exposure_lock": True,
        "hardware_exposure": -6.0,
        "hardware_gain": 95.0,
        "optical_clarity": 1.25,
        "denoise_strength": 0.10,
        "film_look": "Leica Monochrome",
        "lut_intensity": 100.0,
        "shadows_lift": -6.0,
        "midtones_gamma": 0.96,
        "highlights_gain": 8.0,
        "scurve_contrast": 0.34,
        "vibrance": 0.0,
        "optical_vignette": 0.32,
        "film_grain": 0.22,
        "ai_mode": "Studio Spotlight (Dim Background)",
        "spotlight_dim_pct": 65.0,
    },
}


class PresetManager:
    """Manages factory and user-created studio presets stored in JSON."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.preset_file = self.storage_dir / "c270_optix_presets.json"
        self.user_presets: Dict[str, Dict[str, Any]] = {}
        self.load_from_disk()

    def load_from_disk(self) -> None:
        if not self.preset_file.exists():
            self.user_presets = {}
            self.save_to_disk()
            return
        try:
            with open(self.preset_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.user_presets = data
        except Exception:
            self.user_presets = {}

    def save_to_disk(self) -> None:
        try:
            with open(self.preset_file, "w", encoding="utf-8") as f:
                json.dump(self.user_presets, f, indent=2)
        except Exception:
            pass

    def list_preset_names(self) -> List[str]:
        names = list(FACTORY_PRESETS.keys())
        for name in sorted(self.user_presets.keys()):
            if name not in names:
                names.append(name)
        return names

    def get_preset(self, name: str) -> Dict[str, Any]:
        base = copy.deepcopy(DEFAULT_STUDIO_PARAMS)
        if name in self.user_presets:
            base.update(copy.deepcopy(self.user_presets[name]))
        elif name in FACTORY_PRESETS:
            base.update(copy.deepcopy(FACTORY_PRESETS[name]))
        return base

    def save_user_preset(self, name: str, params: Dict[str, Any]) -> None:
        clean_name = name.strip()
        if not clean_name:
            return
        self.user_presets[clean_name] = copy.deepcopy(params)
        self.save_to_disk()

    def delete_user_preset(self, name: str) -> bool:
        if name in self.user_presets:
            del self.user_presets[name]
            self.save_to_disk()
            return True
        return False
