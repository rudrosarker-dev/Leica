# -*- coding: utf-8 -*-
"""
Minimalist, Spacious 3-Part Studio Window (`ui/main_window.py`).
Inspired by Camo Studio, Apple Final Cut, and Leica FOTOS:
1. Minimal Top Header Bar (Height: 52px, #0D0D10)
2. Left/Center Hero Viewport (76% width, 24px breathing margin, + 68px Bottom Capture Bar)
3. Single Right Studio Sidebar (Fixed Width: 350px, #111115) with 4 clean sequential tabs:
   `1. Light` | `2. Color` | `3. Frame` | `4. Studio`
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QInputDialog,
    QMessageBox,
)

from core.camera_engine import CameraWorker
from core.color_lut import STUDIO_LOOK_NAMES
from core.preset_manager import PresetManager, DEFAULT_STUDIO_PARAMS
from core.recorder_audio import AudioVUMonitor, StudioRecorder, VirtualCamManager
from ui.viewport_hud import ViewportCanvas
from ui.widgets import (
    PrecisionSlider,
    ToggleSwitch,
    SegmentedBar,
    ShutterButton,
    RecordButton,
    InspectorCard,
    ApertureLogoWidget,
    escape_qt_mnemonic,
)


class MainWindow(QMainWindow):
    """Minimalist 3-Part Studio Window for Optix Studio (`1360 x 820`)."""

    def __init__(self, output_dir: Path) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.setWindowTitle("Optix Studio")
        self.resize(1360, 820)
        self.setMinimumSize(1120, 700)

        self.preset_manager = PresetManager(self.output_dir)
        self.audio_monitor = AudioVUMonitor(self)
        self.recorder = StudioRecorder(self.output_dir, self.audio_monitor, self)
        self.virtual_cam = VirtualCamManager(self)
        self.camera_worker = CameraWorker(self.output_dir, self)
        self.camera_worker.recorder_hook = self.recorder
        self.camera_worker.virtual_cam_hook = self.virtual_cam

        self._countdown_remaining = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self._updating_ui = False
        self._look_buttons: Dict[str, QPushButton] = {}

        self._build_ui()
        self._connect_signals()

        self._refresh_camera_devices()
        self.audio_monitor.start()
        self.camera_worker.start(CameraWorker.Priority.HighPriority)

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. MINIMAL TOP HEADER BAR (Height: 52px)
        root_layout.addWidget(self._build_top_header_bar())

        # 2. MAIN WORKSPACE (Left/Center Hero Column + Single Right Studio Sidebar)
        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # Left/Center Hero Column (~76% width)
        hero_column = QWidget(self)
        hero_layout = QVBoxLayout(hero_column)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(0)

        self.viewport = ViewportCanvas(self)
        hero_layout.addWidget(self.viewport, 1)
        hero_layout.addWidget(self._build_bottom_capture_bar())

        workspace_layout.addWidget(hero_column, 1)
        workspace_layout.addWidget(self._build_right_studio_sidebar())

        root_layout.addLayout(workspace_layout, 1)

    def _build_top_header_bar(self) -> QFrame:
        bar = QFrame(self)
        bar.setObjectName("TopHeaderBar")
        bar.setFixedHeight(52)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Left Cluster: Lens Icon + "Optix Studio" + Camera Selector (240px) + Driver Settings (115px)
        self.logo_icon = ApertureLogoWidget(bar)
        self.brand_label = QLabel("Optix Studio")
        self.brand_label.setObjectName("BrandTitle")

        self.camera_combo = QComboBox(bar)
        self.camera_combo.setFixedSize(240, 32)

        self.btn_driver_settings = QPushButton("Driver Settings", bar)
        self.btn_driver_settings.setFixedSize(115, 32)

        layout.addWidget(self.logo_icon)
        layout.addWidget(self.brand_label)
        layout.addSpacing(6)
        layout.addWidget(self.camera_combo)
        layout.addWidget(self.btn_driver_settings)

        layout.addStretch(1)

        # Center Status Pill: "● 720p HD  |  30.0 FPS" (Width: 160px)
        self.status_pill = QLabel("720p HD  |  30.0 FPS")
        self.status_pill.setFixedSize(160, 30)
        self.status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_pill.setStyleSheet(
            "background-color: #141419; border: 1px solid #24242C; border-radius: 15px; "
            'color: #10B981; font-family: "Consolas", "JetBrains Mono", monospace; font-size: 11px; font-weight: 600;'
        )
        layout.addWidget(self.status_pill)

        layout.addStretch(1)

        # Right Cluster: Pure View (Bypass) (140px) + Reset All (90px) + Gallery (90px)
        self.btn_pure_view = QPushButton("Pure View (Bypass)", bar)
        self.btn_pure_view.setCheckable(True)
        self.btn_pure_view.setFixedSize(140, 32)

        self.btn_reset_all = QPushButton("Reset All", bar)
        self.btn_reset_all.setFixedSize(90, 32)

        self.btn_gallery = QPushButton("Gallery", bar)
        self.btn_gallery.setFixedSize(90, 32)

        layout.addWidget(self.btn_pure_view)
        layout.addWidget(self.btn_reset_all)
        layout.addWidget(self.btn_gallery)

        return bar

    def _build_bottom_capture_bar(self) -> QFrame:
        bar = QFrame(self)
        bar.setObjectName("BottomCaptureBar")
        bar.setFixedHeight(68)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        layout.addStretch(1)

        # 1. Timer Selector (105x34px)
        self.combo_timer = QComboBox(bar)
        self.combo_timer.setFixedSize(105, 34)
        self.combo_timer.addItems(["Timer: Off", "Timer: 3s", "Timer: 5s"])

        # 2. Screen Flash Toggle (110x34px)
        self.btn_flash = QPushButton("Screen Flash", bar)
        self.btn_flash.setCheckable(True)
        self.btn_flash.setFixedSize(110, 34)

        # 3. Primary Photo Shutter Button (50x50px)
        self.btn_shutter = ShutterButton(bar)

        # 4. Primary Video Record Button (50x50px) + Recording Timer Pill (shown only when recording)
        self.btn_record = RecordButton(bar)
        self.lbl_rec_timer = QLabel("00:00:00:00", bar)
        self.lbl_rec_timer.setFixedSize(96, 30)
        self.lbl_rec_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rec_timer.setStyleSheet(
            "background-color: #281117; border: 1px solid #E11D48; border-radius: 6px; "
            'color: #F4F4F6; font-family: "Consolas", monospace; font-size: 11px; font-weight: 700;'
        )
        self.lbl_rec_timer.setVisible(False)

        # 5. Virtual Cam Toggle (135x34px)
        self.btn_vcam = QPushButton("Virtual Cam: Off", bar)
        self.btn_vcam.setObjectName("VirtualCamButton")
        self.btn_vcam.setCheckable(True)
        self.btn_vcam.setFixedSize(135, 34)

        layout.addWidget(self.combo_timer)
        layout.addWidget(self.btn_flash)
        layout.addWidget(self.btn_shutter)
        layout.addWidget(self.btn_record)
        layout.addWidget(self.lbl_rec_timer)
        layout.addWidget(self.btn_vcam)

        layout.addStretch(1)
        return bar

    def _build_right_studio_sidebar(self) -> QFrame:
        sidebar = QFrame(self)
        sidebar.setObjectName("RightStudioSidebar")
        sidebar.setFixedWidth(350)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 4 Clean Sequential Category Tabs (Height: 48px container, 36px buttons)
        tab_header = QWidget(sidebar)
        tab_header.setStyleSheet("background-color: #0D0D10; border-bottom: 1px solid #1E1E24;")
        tab_header_layout = QVBoxLayout(tab_header)
        tab_header_layout.setContentsMargins(12, 8, 12, 8)
        self.sidebar_tabs = SegmentedBar(["1. Light", "2. Color", "3. Frame", "4. Studio"], height=34)
        tab_header_layout.addWidget(self.sidebar_tabs)
        layout.addWidget(tab_header)

        self.sidebar_stack = QStackedWidget(sidebar)
        self.sidebar_stack.addWidget(self._build_tab_1_light())
        self.sidebar_stack.addWidget(self._build_tab_2_color())
        self.sidebar_stack.addWidget(self._build_tab_3_frame())
        self.sidebar_stack.addWidget(self._build_tab_4_studio())

        layout.addWidget(self.sidebar_stack, 1)
        return sidebar

    def _build_tab_1_light(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(14)

        c1 = InspectorCard("QUICK LIGHTING")
        self.sl_light_boost = PrecisionSlider(
            "Smart Light Boost (Dark Room Lift)", 0, 100, 0, step=1, decimals=0, suffix="%"
        )
        self.sl_brightness = PrecisionSlider("Brightness", -100, 100, 0, step=1, decimals=0, bipolar=True)
        self.sl_contrast = PrecisionSlider("Contrast", -100, 100, 0, step=1, decimals=0, bipolar=True)
        self.sl_sharpness = PrecisionSlider("HD Sharpness (Crisp Detail)", 0, 100, 0, step=1, decimals=0, suffix="%")
        self.sl_denoise = PrecisionSlider("Smooth Grain (Denoise)", 0, 100, 0, step=1, decimals=0, suffix="%")

        for sl in (self.sl_light_boost, self.sl_brightness, self.sl_contrast, self.sl_sharpness, self.sl_denoise):
            c1.add_widget(sl)
        vbox.addWidget(c1)

        c2 = InspectorCard("SENSOR HARDWARE (OPTIONAL)")
        self.sw_manual_exp = ToggleSwitch("Manual Hardware Exposure", checked=False)
        self.sl_hw_exp = PrecisionSlider("Hardware Exposure", -10, -2, -4, step=1, decimals=0, suffix=" EV")
        self.sl_hw_gain = PrecisionSlider("Hardware Sensor Gain", 0, 255, 120, step=1, decimals=0)
        self.sl_hw_exp.setEnabled(False)
        self.sl_hw_gain.setEnabled(False)

        c2.add_widget(self.sw_manual_exp)
        c2.add_widget(self.sl_hw_exp)
        c2.add_widget(self.sl_hw_gain)
        vbox.addWidget(c2)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_tab_2_color(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(14)

        c1 = InspectorCard("STUDIO LOOKS")
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, look_name in enumerate(STUDIO_LOOK_NAMES):
            # Escape & as && so "Classic B&W" renders cleanly in Qt
            btn = QPushButton(escape_qt_mnemonic(look_name))
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            if look_name == "Natural (Off)":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, n=look_name: self._on_look_selected(n))
            self._look_buttons[look_name] = btn
            grid.addWidget(btn, i // 2, i % 2)
        c1.add_layout(grid)

        self.sl_look_intensity = PrecisionSlider("Look Intensity", 0, 100, 75, step=1, decimals=0, suffix="%")
        c1.add_widget(self.sl_look_intensity)
        vbox.addWidget(c1)

        c2 = InspectorCard("COLOR BALANCE")
        self.sl_warmth = PrecisionSlider("Warmth (Temperature)", -100, 100, 0, step=1, decimals=0, bipolar=True)
        self.sl_tint = PrecisionSlider("Tint", -100, 100, 0, step=1, decimals=0, bipolar=True)
        self.sl_saturation = PrecisionSlider("Saturation (Vibrance)", -100, 100, 0, step=1, decimals=0, bipolar=True)
        self.sl_vignette = PrecisionSlider("Soft Vignette", 0, 100, 0, step=1, decimals=0, suffix="%")

        for sl in (self.sl_warmth, self.sl_tint, self.sl_saturation, self.sl_vignette):
            c2.add_widget(sl)
        vbox.addWidget(c2)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_tab_3_frame(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(14)

        c1 = InspectorCard("CAMERA FRAMING")
        self.sl_zoom = PrecisionSlider("Digital Zoom", 1.00, 2.50, 1.00, step=0.02, decimals=2, suffix="x")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_mirror = QPushButton("Mirror Video")
        self.btn_mirror.setCheckable(True)
        self.btn_mirror.setChecked(True)
        self.btn_mirror.setFixedHeight(34)

        self.btn_rotate = QPushButton("Rotate 90°")
        self.btn_rotate.setFixedHeight(34)

        self.btn_center_frame = QPushButton("Center Frame")
        self.btn_center_frame.setFixedHeight(34)

        btn_row.addWidget(self.btn_mirror)
        btn_row.addWidget(self.btn_rotate)
        btn_row.addWidget(self.btn_center_frame)

        self.sw_grid = ToggleSwitch("Show Composition Grid", checked=False)
        self.sw_cinema_bars = ToggleSwitch("Cinema Widescreen Bars (2.35:1)", checked=False)

        c1.add_widget(self.sl_zoom)
        c1.add_layout(btn_row)
        c1.add_widget(self.sw_grid)
        c1.add_widget(self.sw_cinema_bars)
        vbox.addWidget(c1)

        c2 = InspectorCard("PORTRAIT BACKGROUND")
        self.combo_bg_mode = QComboBox()
        self.combo_bg_mode.setFixedHeight(34)
        self.combo_bg_mode.addItems(
            [
                "Off (Natural Background)",
                "Portrait Bokeh Blur",
                "Studio Dimmed Background (Spotlight)",
            ]
        )
        self.sl_bg_strength = PrecisionSlider("Effect Strength", 10, 100, 50, step=1, decimals=0, suffix="%")
        self.sw_auto_frame = ToggleSwitch("AI Auto-Frame Face", checked=False)

        c2.add_widget(self.combo_bg_mode)
        c2.add_widget(self.sl_bg_strength)
        c2.add_widget(self.sw_auto_frame)
        vbox.addWidget(c2)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_tab_4_studio(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(14)

        c1 = InspectorCard("SAVED PRESETS")
        self.combo_preset = QComboBox()
        self.combo_preset.setFixedHeight(34)
        self._reload_preset_combo()

        preset_btn_row = QHBoxLayout()
        preset_btn_row.setSpacing(8)
        self.btn_save_preset = QPushButton("Save Current Preset")
        self.btn_save_preset.setFixedHeight(34)
        self.btn_del_preset = QPushButton("Delete Preset")
        self.btn_del_preset.setFixedHeight(34)
        preset_btn_row.addWidget(self.btn_save_preset)
        preset_btn_row.addWidget(self.btn_del_preset)

        c1.add_widget(self.combo_preset)
        c1.add_layout(preset_btn_row)
        vbox.addWidget(c1)

        c2 = InspectorCard("OUTPUT QUALITY && OVERLAY")
        self.seg_res = SegmentedBar(["720p Fast (30 FPS)", "1080p Upscaled"], height=34)
        self.seg_fmt = SegmentedBar(["PNG (Lossless)", "JPG (High Quality)"], height=34)

        self.sw_lower_third = ToggleSwitch("Show Name Tag (Lower Third)", checked=False)
        self.ed_lt_name = QLineEdit("Alex Morgan")
        self.ed_lt_name.setPlaceholderText("Your Name")
        self.ed_lt_title = QLineEdit("Product Design Lead")
        self.ed_lt_title.setPlaceholderText("Your Title / Role")

        self.sw_corner_hud = ToggleSwitch("Show Corner Histogram & Mic Meter", checked=False)

        c2.add_widget(self.seg_res)
        c2.add_widget(self.seg_fmt)
        c2.add_widget(self.sw_lower_third)
        c2.add_widget(self.ed_lt_name)
        c2.add_widget(self.ed_lt_title)
        c2.add_widget(self.sw_corner_hud)
        vbox.addWidget(c2)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _connect_signals(self) -> None:
        # Header Bar
        self.camera_combo.currentIndexChanged.connect(self._on_device_changed)
        self.btn_driver_settings.clicked.connect(self.camera_worker.request_driver_settings_dialog)
        self.btn_pure_view.toggled.connect(lambda v: self._set_param("pure_view_bypass", v))
        self.btn_reset_all.clicked.connect(self._on_reset_all)
        self.btn_gallery.clicked.connect(self._on_open_gallery)

        # Sidebar Tabs
        self.sidebar_tabs.indexChanged.connect(self.sidebar_stack.setCurrentIndex)

        # Tab 1: Light
        self.sl_light_boost.valueChanged.connect(lambda v: self._set_param("light_boost", v))
        self.sl_brightness.valueChanged.connect(lambda v: self._set_param("brightness", v))
        self.sl_contrast.valueChanged.connect(lambda v: self._set_param("contrast", v))
        self.sl_sharpness.valueChanged.connect(lambda v: self._set_param("sharpness", v))
        self.sl_denoise.valueChanged.connect(lambda v: self._set_param("denoise", v))
        self.sw_manual_exp.toggled.connect(self._on_manual_exp_toggled)
        self.sl_hw_exp.valueChanged.connect(lambda v: self._set_param("hardware_exposure", v))
        self.sl_hw_gain.valueChanged.connect(lambda v: self._set_param("hardware_gain", v))

        # Tab 2: Color
        self.sl_look_intensity.valueChanged.connect(lambda v: self._set_param("look_intensity", v))
        self.sl_warmth.valueChanged.connect(lambda v: self._set_param("warmth", v))
        self.sl_tint.valueChanged.connect(lambda v: self._set_param("tint", v))
        self.sl_saturation.valueChanged.connect(lambda v: self._set_param("saturation", v))
        self.sl_vignette.valueChanged.connect(lambda v: self._set_param("vignette", v))

        # Tab 3: Frame
        self.sl_zoom.valueChanged.connect(self._on_zoom_slider_changed)
        self.btn_mirror.toggled.connect(lambda v: self._set_param("mirror_h", v))
        self.btn_rotate.clicked.connect(self._on_rotate_clicked)
        self.btn_center_frame.clicked.connect(self._on_reset_ptz)
        self.sw_grid.toggled.connect(self._on_viewport_guides_changed)
        self.sw_cinema_bars.toggled.connect(self._on_viewport_guides_changed)
        self.combo_bg_mode.currentTextChanged.connect(lambda t: self._set_param("bg_mode", t))
        self.sl_bg_strength.valueChanged.connect(lambda v: self._set_param("bg_strength", v))
        self.sw_auto_frame.toggled.connect(lambda v: self._set_param("auto_frame_face", v))

        # Tab 4: Studio
        self.combo_preset.currentTextChanged.connect(self._on_preset_selected)
        self.btn_save_preset.clicked.connect(self._on_save_preset)
        self.btn_del_preset.clicked.connect(self._on_delete_preset)
        self.seg_res.indexChanged.connect(lambda idx: self._set_param("upscale_1080p", idx == 1))
        self.seg_fmt.indexChanged.connect(
            lambda idx: self._set_param("photo_format", "JPG (High Quality)" if idx == 1 else "PNG (Lossless)")
        )
        self.sw_lower_third.toggled.connect(lambda v: self._set_param("show_lower_third", v))
        self.ed_lt_name.textChanged.connect(lambda t: self._set_param("lower_third_name", t))
        self.ed_lt_title.textChanged.connect(lambda t: self._set_param("lower_third_title", t))
        self.sw_corner_hud.toggled.connect(self._on_corner_hud_toggled)

        # Viewport Interactive PTZ
        self.viewport.ptz_changed.connect(self._on_viewport_ptz_dragged)
        self.viewport.ptz_reset_requested.connect(self._on_reset_ptz)
        self.viewport.flash_peak_reached.connect(self._execute_immediate_snapshot)

        # Capture Bar
        self.btn_shutter.clicked.connect(self._on_shutter_clicked)
        self.btn_record.clicked.connect(self._on_record_clicked)
        self.btn_vcam.toggled.connect(self._on_vcam_toggled)

        # Worker & Audio Signals
        self.camera_worker.frame_ready.connect(self._on_frame_ready)
        self.audio_monitor.levels_updated.connect(self.viewport.set_audio_levels)
        self.recorder.recording_state_changed.connect(self._on_recording_state_changed)
        self.recorder.timecode_updated.connect(self.lbl_rec_timer.setText)
        self.virtual_cam.status_changed.connect(self._on_vcam_status)

    def _refresh_camera_devices(self) -> None:
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        for idx, name in CameraWorker.enumerate_cameras():
            self.camera_combo.addItem(name, idx)
        self.camera_combo.blockSignals(False)
        self._on_device_changed()

    def _on_device_changed(self) -> None:
        idx = self.camera_combo.currentData()
        self.camera_worker.set_device(int(idx) if idx is not None else 0)

    def _set_param(self, key: str, value: Any) -> None:
        if self._updating_ui:
            return
        self.camera_worker.update_param(key, value)

    def _on_manual_exp_toggled(self, checked: bool) -> None:
        self.sl_hw_exp.setEnabled(checked)
        self.sl_hw_gain.setEnabled(checked)
        self._set_param("manual_exposure", checked)

    def _on_look_selected(self, look_name: str) -> None:
        for name, btn in self._look_buttons.items():
            btn.setChecked(name == look_name)
        self._set_param("active_lut", look_name)

    def _on_zoom_slider_changed(self, val: float) -> None:
        if self._updating_ui:
            return
        params = self.camera_worker.get_params_copy()
        self.viewport.set_ptz_targets(val, float(params.get("pan_x", 0.0)), float(params.get("tilt_y", 0.0)))
        self.camera_worker.update_param("digital_zoom", val)

    def _on_viewport_ptz_dragged(self, z: float, px: float, py: float) -> None:
        self._updating_ui = True
        self.sl_zoom.setValue(z)
        self._updating_ui = False
        self.camera_worker.update_param("digital_zoom", z)
        self.camera_worker.update_param("pan_x", px)
        self.camera_worker.update_param("tilt_y", py)

    def _on_rotate_clicked(self) -> None:
        params = self.camera_worker.get_params_copy()
        self.camera_worker.update_param("rotate_quadrant", (int(params.get("rotate_quadrant", 0)) + 1) % 4)

    def _on_reset_ptz(self) -> None:
        self._updating_ui = True
        self.sl_zoom.setValue(1.00)
        self._updating_ui = False
        self.viewport.set_ptz_targets(1.00, 0.00, 0.00)
        self.camera_worker.update_param("digital_zoom", 1.00)
        self.camera_worker.update_param("pan_x", 0.00)
        self.camera_worker.update_param("tilt_y", 0.00)
        self.camera_worker.update_param("rotate_quadrant", 0)

    def _on_viewport_guides_changed(self) -> None:
        self.viewport.show_grid = self.sw_grid.isChecked()
        self.viewport.show_cinema_bars = self.sw_cinema_bars.isChecked()
        self.viewport.update()

    def _on_corner_hud_toggled(self, checked: bool) -> None:
        self.viewport.show_corner_hud = checked
        self._set_param("show_corner_hud", checked)
        self.viewport.update()

    def _on_frame_ready(self, frame_bgr, telemetry: Dict[str, Any]) -> None:
        self.viewport.update_frame(frame_bgr, telemetry)
        res_label = "1080p HQ" if telemetry.get("upscaled", False) else "720p HD"
        fps = float(telemetry.get("fps", 30.0))
        self.status_pill.setText(f"{res_label}  |  {fps:4.1f} FPS")

    def _reload_preset_combo(self, select_name: str = "") -> None:
        self.combo_preset.blockSignals(True)
        self.combo_preset.clear()
        names = self.preset_manager.list_preset_names()
        self.combo_preset.addItems(names)
        if select_name and select_name in names:
            self.combo_preset.setCurrentText(select_name)
        self.combo_preset.blockSignals(False)

    def _apply_params_to_ui(self, params: Dict[str, Any]) -> None:
        self._updating_ui = True
        try:
            self.btn_pure_view.setChecked(bool(params.get("pure_view_bypass", False)))
            self.sl_light_boost.setValue(float(params.get("light_boost", 0.0)))
            self.sl_brightness.setValue(float(params.get("brightness", 0.0)))
            self.sl_contrast.setValue(float(params.get("contrast", 0.0)))
            self.sl_sharpness.setValue(float(params.get("sharpness", 0.0)))
            self.sl_denoise.setValue(float(params.get("denoise", 0.0)))

            man_exp = bool(params.get("manual_exposure", False))
            self.sw_manual_exp.setChecked(man_exp)
            self.sl_hw_exp.setEnabled(man_exp)
            self.sl_hw_gain.setEnabled(man_exp)
            self.sl_hw_exp.setValue(float(params.get("hardware_exposure", -4.0)))
            self.sl_hw_gain.setValue(float(params.get("hardware_gain", 120.0)))

            look = str(params.get("active_lut", "Natural (Off)"))
            for name, btn in self._look_buttons.items():
                btn.setChecked(name == look)
            self.sl_look_intensity.setValue(float(params.get("look_intensity", 75.0)))
            self.sl_warmth.setValue(float(params.get("warmth", 0.0)))
            self.sl_tint.setValue(float(params.get("tint", 0.0)))
            self.sl_saturation.setValue(float(params.get("saturation", 0.0)))
            self.sl_vignette.setValue(float(params.get("vignette", 0.0)))

            self.sl_zoom.setValue(float(params.get("digital_zoom", 1.00)))
            self.btn_mirror.setChecked(bool(params.get("mirror_h", True)))
            self.sw_grid.setChecked(bool(params.get("show_grid", False)))
            self.sw_cinema_bars.setChecked(bool(params.get("show_cinema_bars", False)))
            self.combo_bg_mode.setCurrentText(str(params.get("bg_mode", "Off (Natural Background)")))
            self.sl_bg_strength.setValue(float(params.get("bg_strength", 50.0)))
            self.sw_auto_frame.setChecked(bool(params.get("auto_frame_face", False)))

            self.seg_res.set_current_index(1 if params.get("upscale_1080p", False) else 0)
            self.seg_fmt.set_current_index(1 if "JPG" in str(params.get("photo_format", "")) else 0)
            self.sw_lower_third.setChecked(bool(params.get("show_lower_third", False)))
            self.ed_lt_name.setText(str(params.get("lower_third_name", "Alex Morgan")))
            self.ed_lt_title.setText(str(params.get("lower_third_title", "Product Design Lead")))
            self.sw_corner_hud.setChecked(bool(params.get("show_corner_hud", False)))

            self.viewport.show_grid = bool(params.get("show_grid", False))
            self.viewport.show_cinema_bars = bool(params.get("show_cinema_bars", False))
            self.viewport.show_corner_hud = bool(params.get("show_corner_hud", False))
        finally:
            self._updating_ui = False

        self.camera_worker.update_all_params(params)
        self.viewport.update()

    def _on_preset_selected(self, name: str) -> None:
        if name:
            self._apply_params_to_ui(self.preset_manager.get_preset(name))

    def _on_save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Studio Preset", "Preset Name:", text="My Custom Look")
        if ok and name.strip():
            self.preset_manager.save_user_preset(name.strip(), self.camera_worker.get_params_copy())
            self._reload_preset_combo(select_name=name.strip())

    def _on_delete_preset(self) -> None:
        cur = self.combo_preset.currentText()
        if self.preset_manager.delete_user_preset(cur):
            self._reload_preset_combo()
        else:
            QMessageBox.information(self, "Preset Protected", "Built-in studio presets cannot be deleted.")

    def _on_reset_all(self) -> None:
        self.combo_preset.blockSignals(True)
        self.combo_preset.setCurrentText("Default (Pure Natural)")
        self.combo_preset.blockSignals(False)
        self._apply_params_to_ui(DEFAULT_STUDIO_PARAMS)

    def _on_shutter_clicked(self) -> None:
        t = self.combo_timer.currentText()
        if "3s" in t:
            self._start_countdown(3)
        elif "5s" in t:
            self._start_countdown(5)
        else:
            self._trigger_flash_or_snapshot()

    def _start_countdown(self, sec: int) -> None:
        self._countdown_remaining = sec
        self.viewport.set_countdown(sec)
        self._countdown_timer.start()

    def _on_countdown_tick(self) -> None:
        self._countdown_remaining -= 1
        if self._countdown_remaining > 0:
            self.viewport.set_countdown(self._countdown_remaining)
        else:
            self._countdown_timer.stop()
            self.viewport.set_countdown(0)
            self._trigger_flash_or_snapshot()

    def _trigger_flash_or_snapshot(self) -> None:
        if self.btn_flash.isChecked():
            self.viewport.trigger_softbox_flash()
        else:
            self._execute_immediate_snapshot()

    def _execute_immediate_snapshot(self) -> None:
        params = self.camera_worker.get_params_copy()
        self.camera_worker.trigger_snapshot(fmt=str(params.get("photo_format", "PNG (Lossless)")), count=1)

    def _on_record_clicked(self) -> None:
        if not self.recorder.is_recording:
            params = self.camera_worker.get_params_copy()
            w, h = (1920, 1080) if params.get("upscale_1080p", False) else (1280, 720)
            self.recorder.start_recording(width=w, height=h, fps=30.0)
        else:
            self.recorder.stop_recording()

    def _on_recording_state_changed(self, is_recording: bool, is_paused: bool) -> None:
        self.btn_record.setChecked(is_recording)
        self.lbl_rec_timer.setVisible(is_recording)
        self.viewport.set_tally_state(is_recording, self.virtual_cam.is_active)

    def _on_vcam_toggled(self, checked: bool) -> None:
        params = self.camera_worker.get_params_copy()
        w, h = (1920, 1080) if params.get("upscale_1080p", False) else (1280, 720)
        ok = self.virtual_cam.set_enabled(checked, width=w, height=h)
        if checked and not ok:
            self.btn_vcam.blockSignals(True)
            self.btn_vcam.setChecked(False)
            self.btn_vcam.setText("Virtual Cam: Off")
            self.btn_vcam.blockSignals(False)

    def _on_vcam_status(self, active: bool, msg: str) -> None:
        self.btn_vcam.setText("Virtual Cam: On" if active else "Virtual Cam: Off")
        self.viewport.set_tally_state(self.recorder.is_recording, active)

    def _on_open_gallery(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(self.output_dir))  # type: ignore
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(self.output_dir)])
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        self.virtual_cam.stop()
        self.audio_monitor.stop()
        self.camera_worker.stop_worker()
        super().closeEvent(event)
