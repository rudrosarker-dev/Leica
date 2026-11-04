# -*- coding: utf-8 -*-
"""
UI Package for LEICA // C270 OPTIX STUDIO ("Obsidian Leica Matte" Industrial Design System).
"""

from ui.styles import OBSIDIAN_LEICA_STYLESHEET
from ui.widgets import (
    PrecisionSlider,
    ToggleSwitch,
    SegmentedBar,
    ShutterButton,
    RecordButton,
    PauseRecordButton,
    InspectorCard,
    ApertureLogoWidget,
    RefreshIconButton,
)
from ui.viewport_hud import ViewportCanvas
from ui.main_window import MainWindow

__all__ = [
    "OBSIDIAN_LEICA_STYLESHEET",
    "PrecisionSlider",
    "ToggleSwitch",
    "SegmentedBar",
    "ShutterButton",
    "RecordButton",
    "PauseRecordButton",
    "InspectorCard",
    "ApertureLogoWidget",
    "RefreshIconButton",
    "ViewportCanvas",
    "MainWindow",
]
