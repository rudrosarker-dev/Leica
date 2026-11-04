# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — Preset Management System & Hardware Calibration Profiles (`core/preset_manager.py`).
Defines exact Logitech C270 DirectShow hardware defaults, 30-FPS Anti-Lag Boost defaults,
and the 12 One-Click Studio Presets with custom JSON import/export support.
"""

import copy
import json
from pathlib import Path
from typing import Dict, Any, List


# Exact Native Logitech C270 DirectShow Hardware Factory Defaults
C270_NATIVE_HW_DEFAULTS: Dict[str, Any] = {
    "hw_brightness": 128,      # Range 0..255, Native Default = 128
    "hw_contrast": 32,         # Range 0..255, Native Default = 32 (NEVER 135)
    "hw_saturation": 32,       # Range 0..255, Native Default = 32 (NEVER 132)
    "hw_sharpness": 24,        # Range 0..255, Native Default = 24 (NEVER 140)
    "hw_gain": 100,            # Range 0..255, Native Default = 100
    "hw_backlight": 0,         # Range 0..2, Native Default = 0 (0 = Low Light Comp OFF -> 30 FPS)
    "hw_exposure": -4,         # Range -11..-2, Native Default = -4 EV
    "hw_powerline_hz": 1,      # 1 = 50 Hz Anti-Flicker
    "hw_auto_wb": True,        # Auto White Balance ON
}


DEFAULT_STUDIO_PARAMS: Dict[str, Any] = {
    # Master Bypass
    "pure_view_bypass": False,
    "active_preset_name": "01. Pure Natural 30FPS",

    # MODE 1: 1. EXPOSURE & LIGHT
    # Card 1: Lighting & Clarity
    "light_boost": 25.0,           # Smart Room Light Boost (Shadow Lift) 0..100%, Default 25% when 30-FPS Boost ON
    "brightness": 0.0,             # Digital Brightness -100..+100, Default 0
    "contrast": 0.0,               # Micro-Contrast -100..+100, Default 0
    "sharpness": 15.0,             # Optical Sharpness (HD Crisp) 0..100%, Default 15%
    "denoise": 0.0,                # Low-Light Denoise 0..100%, Default 0%

    # Card 2: C270 Sensor Hardware — Exact Native Ranges
    "unlock_30fps": True,          # Toggle: Unlock 30 FPS (Disable Low-Light Lag), Default: ON
    "hardware_exposure": -4,       # Sensor Shutter (Exposure) -11..-2, Default: -4 EV
    "hardware_gain": 130,          # Sensor ISO Gain 0..255, Default: 130 (or 140 in boost)
    "hw_brightness": 128,          # Hardware Brightness 0..255, Default: 128
    "hw_contrast": 32,             # Hardware Contrast 0..255, Default: 32
    "hw_saturation": 32,           # Hardware Saturation 0..255, Default: 32
    "hw_sharpness": 24,            # Hardware Sharpness 0..255, Default: 24
    "hw_backlight": 0,             # Low Light Compensation: 0 = OFF (30 FPS), 1 = ON (10 FPS)
    "hw_powerline_hz": 1,          # 1 = 50 Hz Anti-Flicker
    "hw_auto_wb": True,

    # MODE 2: 2. COLOR & LUTS
    "active_lut": "Pure Natural (Off)",
    "look_intensity": 75.0,        # 0% to 100%, Default: 75%
    "custom_cube_path": "",
    "warmth": 0.0,                 # Color Temperature (Warmth) -100 Cool to +100 Warm, Default: 0
    "tint": 0.0,                   # Tint (Green / Magenta) -100 to +100, Default: 0
    "saturation": 0.0,             # Vibrance (Rich Color) -100 to +100, Default: 0
    "vignette": 0.0,               # Optical Lens Vignette 0% to 100%, Default: 0%

    # MODE 3: 3. OPTICS & AI
    "digital_zoom": 1.00,          # Optical-Feel Zoom 1.00x to 3.00x, Default: 1.00x
    "pan_x": 0.00,                 # Pan X -1.0 to +1.0
    "tilt_y": 0.00,                # Tilt Y -1.0 to +1.0
    "mirror_h": True,              # Mirror Video (Default ON)
    "flip_v": False,               # Flip V (Default OFF)
    "rotate_quadrant": 0,          # 0, 1, 2, 3 (Rotate 90 deg steps)
    "aspect_mode": "16:9",         # "16:9" or "9:16"
    "bg_mode": "Off (Natural)",    # Off (Natural), Optical Bokeh Blur, Studio Dimmed Spotlight, Custom Backdrop
    "bg_strength": 50.0,           # Blur / Dim Strength 10% to 100%, Default: 50%
    "custom_backdrop_path": "",
    "auto_frame_face": False,      # AI Face Auto-Framing (Center Stage)
    "skin_softening": 0.0,         # Portrait Skin Softening 0% to 100%, Default: 0%
    "show_grid": False,            # Rule of Thirds Grid
    "show_cinema_bars": False,     # 2.35:1 Cinema Scope Bars
    "show_corner_hud": False,      # Show Corner RGB Histogram
    "show_lower_third": False,     # Show Lower-Third Name Tag
    "lower_third_name": "Alex Morgan",
    "lower_third_title": "Cinema Systems Architect",

    # MODE 4: 4. PRESETS (12) & OUTPUT
    "upscale_1080p": False,        # False = 720p 30FPS Native, True = 1080p Lanczos4
    "photo_format": "PNG (Lossless)",
}


FACTORY_PRESETS: Dict[str, Dict[str, Any]] = {
    "01. Pure Natural 30FPS": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "01. Pure Natural 30FPS",
        "unlock_30fps": True,
        "light_boost": 25.0,
        "sharpness": 15.0,
        "active_lut": "Pure Natural (Off)",
    },
    "02. Dark Room Bright 30FPS": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "02. Dark Room Bright 30FPS",
        "unlock_30fps": True,
        "light_boost": 58.0,
        "brightness": 12.0,
        "contrast": 8.0,
        "sharpness": 20.0,
        "denoise": 22.0,
        "hardware_exposure": -4,
        "hardware_gain": 165,
        "active_lut": "Warm Studio",
        "look_intensity": 55.0,
    },
    "03. Pro Zoom / Meet HD": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "03. Pro Zoom / Meet HD",
        "unlock_30fps": True,
        "light_boost": 28.0,
        "brightness": 4.0,
        "contrast": 10.0,
        "sharpness": 28.0,
        "denoise": 12.0,
        "active_lut": "Clean Daylight",
        "look_intensity": 65.0,
        "warmth": 4.0,
        "saturation": 8.0,
        "bg_mode": "Studio Dimmed Spotlight",
        "bg_strength": 35.0,
    },
    "04. YouTube Creator Warm": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "04. YouTube Creator Warm",
        "unlock_30fps": True,
        "light_boost": 30.0,
        "contrast": 16.0,
        "sharpness": 24.0,
        "active_lut": "Warm Studio",
        "look_intensity": 80.0,
        "warmth": 14.0,
        "saturation": 14.0,
        "vignette": 15.0,
        "bg_mode": "Optical Bokeh Blur",
        "bg_strength": 55.0,
    },
    "05. Podcast Moody Studio": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "05. Podcast Moody Studio",
        "unlock_30fps": True,
        "light_boost": 18.0,
        "contrast": 22.0,
        "sharpness": 20.0,
        "active_lut": "Matte Obsidian",
        "look_intensity": 80.0,
        "warmth": 10.0,
        "vignette": 32.0,
        "bg_mode": "Studio Dimmed Spotlight",
        "bg_strength": 55.0,
    },
    "06. Daylight Window Fix": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "06. Daylight Window Fix",
        "unlock_30fps": True,
        "light_boost": 14.0,
        "brightness": -6.0,
        "contrast": 12.0,
        "sharpness": 18.0,
        "hardware_exposure": -5,
        "hardware_gain": 105,
        "active_lut": "Clean Daylight",
        "look_intensity": 70.0,
        "warmth": -6.0,
    },
    "07. Kodak Portra Film": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "07. Kodak Portra Film",
        "unlock_30fps": True,
        "light_boost": 26.0,
        "contrast": 14.0,
        "sharpness": 12.0,
        "active_lut": "Kodak Portra",
        "look_intensity": 85.0,
        "warmth": 12.0,
        "saturation": 10.0,
        "vignette": 20.0,
    },
    "08. Cinema Anamorphic": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "08. Cinema Anamorphic",
        "unlock_30fps": True,
        "light_boost": 24.0,
        "contrast": 20.0,
        "sharpness": 22.0,
        "active_lut": "Cinema Teal/Amber",
        "look_intensity": 88.0,
        "saturation": 12.0,
        "vignette": 24.0,
        "show_cinema_bars": True,
    },
    "09. Portrait DSLR Bokeh": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "09. Portrait DSLR Bokeh",
        "unlock_30fps": True,
        "light_boost": 28.0,
        "contrast": 8.0,
        "sharpness": 16.0,
        "active_lut": "Soft Peach Skin",
        "look_intensity": 75.0,
        "warmth": 8.0,
        "skin_softening": 45.0,
        "bg_mode": "Optical Bokeh Blur",
        "bg_strength": 75.0,
    },
    "10. Leica Monochrome B&W": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "10. Leica Monochrome B&W",
        "unlock_30fps": True,
        "light_boost": 22.0,
        "contrast": 28.0,
        "sharpness": 32.0,
        "active_lut": "Leica B&W",
        "look_intensity": 100.0,
        "vignette": 28.0,
    },
    "11. Neon Cyber Night": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "11. Neon Cyber Night",
        "unlock_30fps": True,
        "light_boost": 32.0,
        "contrast": 24.0,
        "sharpness": 30.0,
        "active_lut": "Cinema Teal/Amber",
        "look_intensity": 92.0,
        "warmth": -18.0,
        "tint": 22.0,
        "saturation": 26.0,
        "vignette": 22.0,
    },
    "12. Broadcast News Clean": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "active_preset_name": "12. Broadcast News Clean",
        "unlock_30fps": True,
        "light_boost": 28.0,
        "contrast": 14.0,
        "sharpness": 34.0,
        "denoise": 10.0,
        "active_lut": "Clean Daylight",
        "look_intensity": 70.0,
        "saturation": 6.0,
        "show_lower_third": True,
    },
}

PRESET_DESCRIPTIONS: Dict[str, str] = {
    "01. Pure Natural 30FPS": "Clean 30FPS with natural light",
    "02. Dark Room Bright 30FPS": "High shadow lift + gain for dim bedrooms at 30FPS",
    "03. Pro Zoom / Meet HD": "Crisp sharpness, balanced skin tone, subtle spotlight",
    "04. YouTube Creator Warm": "Warm tungsten key light feel, rich contrast, bokeh",
    "05. Podcast Moody Studio": "Dimmed background spotlight 55%, warm skin, vignette",
    "06. Daylight Window Fix": "Balanced highlight roll-off for bright windows",
    "07. Kodak Portra Film": "Golden vintage analog film look",
    "08. Cinema Anamorphic": "Teal & Amber grade + 2.35:1 cinema widescreen bars",
    "09. Portrait DSLR Bokeh": "Soft skin retouch + deep optical background blur",
    "10. Leica Monochrome B&W": "High-contrast silver-halide black & white",
    "11. Neon Cyber Night": "Cool shadows, vibrant highlights, crisp edges",
    "12. Broadcast News Clean": "High clarity, neutral white balance, lower-third active",
}


class PresetManager:
    """Manages the 12 factory studio presets and custom user presets in ~/Pictures/Lumixa_C270_Studio/."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.preset_file = self.storage_dir / "lumixa_pro_c270_presets.json"
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

    def list_factory_preset_names(self) -> List[str]:
        return list(FACTORY_PRESETS.keys())

    def list_user_preset_names(self) -> List[str]:
        return sorted(self.user_presets.keys())

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
        base["active_preset_name"] = name
        return base

    def save_user_preset(self, name: str, params: Dict[str, Any]) -> None:
        clean_name = name.strip()
        if not clean_name:
            return
        saved = copy.deepcopy(params)
        saved["active_preset_name"] = clean_name
        self.user_presets[clean_name] = saved
        self.save_to_disk()

    def delete_user_preset(self, name: str) -> bool:
        if name in self.user_presets:
            del self.user_presets[name]
            self.save_to_disk()
            return True
        return False

    def export_presets_json(self, target_path: Path) -> bool:
        try:
            payload = {
                "app": "LUMIXA PRO // C270 CINEMA STUDIO",
                "user_presets": self.user_presets,
            }
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return True
        except Exception:
            return False

    def import_presets_json(self, source_path: Path) -> int:
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                presets_dict = data.get("user_presets", data)
                if isinstance(presets_dict, dict):
                    count = 0
                    for k, v in presets_dict.items():
                        if isinstance(v, dict):
                            self.user_presets[str(k)] = v
                            count += 1
                    self.save_to_disk()
                    return count
        except Exception:
            pass
        return 0
