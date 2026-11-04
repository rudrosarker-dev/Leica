# -*- coding: utf-8 -*-
"""
Core ISP, Hardware UVC, Color LUT, AI Segmentation, Audio/Video Recorder, and Preset Engine
for Optix Studio.
"""

from core.preset_manager import PresetManager, DEFAULT_STUDIO_PARAMS, FACTORY_PRESETS
from core.color_lut import ColorLUTEngine, STUDIO_LOOK_NAMES, FILM_LOOK_NAMES
from core.ai_processor import AIProcessor
from core.recorder_audio import AudioVUMonitor, StudioRecorder, VirtualCamManager
from core.camera_engine import CameraWorker

__all__ = [
    "PresetManager",
    "DEFAULT_STUDIO_PARAMS",
    "FACTORY_PRESETS",
    "ColorLUTEngine",
    "STUDIO_LOOK_NAMES",
    "FILM_LOOK_NAMES",
    "AIProcessor",
    "AudioVUMonitor",
    "StudioRecorder",
    "VirtualCamManager",
    "CameraWorker",
]
