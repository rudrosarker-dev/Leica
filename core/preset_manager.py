# -*- coding: utf-8 -*-
"""
Preset Management System & Pure Natural Startup Defaults (`core/preset_manager.py`).
Every parameter defaults to 100% Pure Sensor Passthrough on startup so the Logitech C270
streams bright, unfiltered 720p video at a locked 30.0 FPS with zero color corruption.
"""

import copy
import json
from pathlib import Path
from typing import Dict, Any, List


DEFAULT_STUDIO_PARAMS: Dict[str, Any] = {
    # Master Bypass
    "pure_view_bypass": False,

    # Tab 1: 1. Light (Quick Lighting + Optional Sensor Hardware)
    "light_boost": 0.0,            # 0% to 100% (Default 0% — pure passthrough)
    "brightness": 0.0,             # -100 to +100 (Default 0)
    "contrast": 0.0,               # -100 to +100 (Default 0)
    "sharpness": 0.0,              # 0% to 100% (Default 0%)
    "denoise": 0.0,                # 0% to 100% (Default 0%)
    "manual_exposure": False,      # Default OFF -> Auto-Exposure (0.75) keeps room bright
    "hardware_exposure": -4.0,     # -10 to -2 EV (Only applied if manual_exposure is True)
    "hardware_gain": 120.0,        # 0 to 255 ISO (Only applied if manual_exposure is True)

    # Tab 2: 2. Color (Studio Looks + Color Balance)
    "active_lut": "Natural (Off)", # Default "Natural (Off)" -> 0% LUT applied
    "look_intensity": 75.0,        # 0% to 100%
    "warmth": 0.0,                 # -100 Cool to +100 Warm (Default 0)
    "tint": 0.0,                   # -100 Green to +100 Magenta (Default 0)
    "saturation": 0.0,             # -100 to +100 (Default 0)
    "vignette": 0.0,               # 0% to 100% (Default 0%)

    # Tab 3: 3. Frame (Camera Framing + Portrait Background)
    "digital_zoom": 1.00,          # 1.00x to 2.50x (Default 1.00x)
    "pan_x": 0.00,                 # -1.00 to +1.00
    "tilt_y": 0.00,                # -1.00 to +1.00
    "mirror_h": True,              # Default ON
    "rotate_quadrant": 0,          # 0, 1, 2, 3
    "show_grid": False,            # Default OFF
    "show_cinema_bars": False,     # Default OFF
    "bg_mode": "Off (Natural Background)",  # Default OFF
    "bg_strength": 50.0,           # 10% to 100% (Default 50%)
    "auto_frame_face": False,      # Default OFF

    # Tab 4: 4. Studio (Saved Presets + Output Quality & Overlay)
    "upscale_1080p": False,        # Default False -> 720p Fast (30 FPS)
    "photo_format": "PNG (Lossless)",
    "show_lower_third": False,     # Default OFF
    "lower_third_name": "Alex Morgan",
    "lower_third_title": "Product Design Lead",
    "show_corner_hud": False,      # Default OFF -> Video stays 100% unobstructed
}


FACTORY_PRESETS: Dict[str, Dict[str, Any]] = {
    "Default (Pure Natural)": copy.deepcopy(DEFAULT_STUDIO_PARAMS),
    "Bright Meeting HD": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "light_boost": 28.0,
        "brightness": 6.0,
        "contrast": 8.0,
        "sharpness": 25.0,
        "denoise": 15.0,
        "active_lut": "Clean Daylight",
        "look_intensity": 65.0,
        "warmth": 4.0,
        "saturation": 8.0,
    },
    "Warm Creator Look": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "light_boost": 22.0,
        "contrast": 12.0,
        "sharpness": 20.0,
        "active_lut": "Warm Studio",
        "look_intensity": 75.0,
        "warmth": 14.0,
        "saturation": 10.0,
        "vignette": 18.0,
        "bg_mode": "Portrait Bokeh Blur",
        "bg_strength": 45.0,
    },
    "Monochrome Film": {
        **copy.deepcopy(DEFAULT_STUDIO_PARAMS),
        "light_boost": 15.0,
        "contrast": 24.0,
        "sharpness": 30.0,
        "active_lut": "Classic B&W",
        "look_intensity": 100.0,
        "vignette": 25.0,
    },
}


class PresetManager:
    """Manages factory and user-saved JSON presets in ~/Pictures/C270_Optix_Studio/."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.preset_file = self.storage_dir / "optix_studio_v2_presets.json"
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
