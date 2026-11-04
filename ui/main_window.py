# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — Tactile 3D/2.5D Cinema Hardware Studio Window (`ui/main_window.py`).

SECTION 3.3 COMPLIANCE:
1. TOP CAMERA TELEMETRY DECK (Height: 54px):
   - Left: 3D Lens Emblem Logo + "LUMIXA PRO" + subtitle "C270 OPTICAL ENGINE" + Camera Selector (220px)
     + "30-FPS BOOST: ON" (3D LED button that unlocks 30 FPS) + "DRIVER PANEL" button.
   - Center: Recessed LCD Digital Telemetry Screen (#08080B inset panel with 1px solid #262632 bezel)
     displaying live: `720P MJPG | FPS: 30.0 | SHUTTER: -4 EV | ISO/GAIN: 130 | SYNC: 1.0X CFR`
   - Right: "PURE VIEW" (1-click bypass LED button), "SYNC GITHUB" (1-click auto-update button),
     "RESET", "GALLERY".
2. CENTER DSLR / CINEMA EVF VIEWFINDER (76% Width):
   - Frames live video inside a dark studio matte box with 20px EVF Corner Reticle Brackets.
   - Bottom EVF Glass Bar (Docked cleanly below the video):
     * Left: Live compact Audio VU Peak Meter (-60dB to 0dB LED segments) + 50Hz Anti-Flicker Status.
     * Center: Tactile Transport Controls — [ Timer ] [ Softbox Flash ] [ 60px 3D SHUTTER ] [ 60px 3D RECORD ] [ Pause ] [ Burst 3x ]
     * Right: [ Virtual Cam LED Toggle ] [ 16:9 / 9:16 Aspect ]
3. RIGHT SEQUENTIAL CONTROL DECK (Fixed Width: 370px, 4 Tactile Hardware Mode Tabs):
   - [ 1. EXPOSURE & LIGHT ] [ 2. COLOR & LUTS ] [ 3. OPTICS & AI ] [ 4. PRESETS (12) ]
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
    QComboBox,
    QLineEdit,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QInputDialog,
    QMessageBox,
    QFileDialog,
)

from core.camera_engine import CameraWorker
from core.color_lut import STUDIO_LOOK_NAMES
from core.github_sync import GitHubSyncManager
from core.preset_manager import (
    PresetManager,
    DEFAULT_STUDIO_PARAMS,
    FACTORY_PRESETS,
    PRESET_DESCRIPTIONS,
)
from core.recorder_audio import AudioVUMonitor, StudioRecorder, VirtualCamManager
from ui.viewport_hud import ViewportCanvas, AudioVUPeakMeterWidget
from ui.widgets import (
    TactileHardwareButton,
    MachinedFaderSlider,
    ToggleSwitch,
    SegmentedBar,
    MechanicalShutterButton,
    CinemaRecordButton,
    InspectorCard,
    Lumixa3DLensWidget,
)


class MainWindow(QMainWindow):
    """Tactile 3D/2.5D Cinema Studio Window for LUMIXA PRO // C270 CINEMA STUDIO."""

    def __init__(self, output_dir: Path) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.setWindowTitle("LUMIXA PRO // C270 CINEMA STUDIO")
        self.resize(1420, 860)
        self.setMinimumSize(1180, 740)

        self.preset_manager = PresetManager(self.output_dir)
        self.audio_monitor = AudioVUMonitor(self)
        self.recorder = StudioRecorder(self.output_dir, self.audio_monitor, self)
        self.virtual_cam = VirtualCamManager(self)
        self.camera_worker = CameraWorker(self.output_dir, self)
        self.camera_worker.recorder_hook = self.recorder
        self.camera_worker.virtual_cam_hook = self.virtual_cam

        self.github_sync = GitHubSyncManager(parent=self)

        self._countdown_remaining = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self._updating_ui = False
        self._look_buttons: Dict[str, TactileHardwareButton] = {}
        self._preset_buttons: Dict[str, TactileHardwareButton] = {}

        self._build_ui()
        self._connect_signals()

        self._refresh_camera_devices()
        self._apply_params_to_ui(DEFAULT_STUDIO_PARAMS)
        self.audio_monitor.start()
        self.camera_worker.start(CameraWorker.Priority.HighPriority)

        # Startup non-blocking GitHub update check
        QTimer.singleShot(1200, self.github_sync.check_for_updates_async)

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. TOP CAMERA TELEMETRY DECK (Height: 54px)
        root_layout.addWidget(self._build_top_telemetry_deck())

        # 2. MAIN WORKSPACE (76% Center DSLR/Cinema EVF Viewfinder + 370px Right Sequential Control Deck)
        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        hero_column = QWidget(self)
        hero_layout = QVBoxLayout(hero_column)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(0)

        self.viewport = ViewportCanvas(self)
        hero_layout.addWidget(self.viewport, 1)
        hero_layout.addWidget(self._build_bottom_evf_glass_bar())

        workspace_layout.addWidget(hero_column, 1)
        workspace_layout.addWidget(self._build_right_control_deck())

        root_layout.addLayout(workspace_layout, 1)

    def _build_top_telemetry_deck(self) -> QFrame:
        bar = QFrame(self)
        bar.setObjectName("TopHeaderBar")
        bar.setFixedHeight(54)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        # Left Cluster: 32x32 3D Lens Emblem + "LUMIXA PRO" / "C270 OPTICAL ENGINE" + Camera Selector + 30-FPS Boost + Driver Panel
        self.logo_icon = Lumixa3DLensWidget(size=34, parent=bar)

        brand_stack = QVBoxLayout()
        brand_stack.setContentsMargins(0, 0, 4, 0)
        brand_stack.setSpacing(0)
        self.brand_label = QLabel("LUMIXA PRO")
        self.brand_label.setObjectName("BrandTitle")
        self.brand_sub = QLabel("C270 OPTICAL ENGINE")
        self.brand_sub.setObjectName("BrandSubtitle")
        brand_stack.addWidget(self.brand_label)
        brand_stack.addWidget(self.brand_sub)

        self.camera_combo = QComboBox(bar)
        self.camera_combo.setFixedSize(210, 32)

        self.btn_30fps_boost = TactileHardwareButton(
            "30-FPS BOOST: ON",
            led_color="emerald",
            checkable=True,
            checked=True,
            parent=bar,
        )
        self.btn_30fps_boost.setFixedSize(142, 32)
        self.btn_30fps_boost.setToolTip(
            "Disables C270 Low Light Compensation (CAP_PROP_BACKLIGHT=0), locks -4 EV shutter, and applies Smart Room Light Boost."
        )

        self.btn_driver_settings = TactileHardwareButton(
            "DRIVER PANEL",
            led_color="none",
            checkable=False,
            parent=bar,
        )
        self.btn_driver_settings.setFixedSize(104, 32)

        layout.addWidget(self.logo_icon)
        layout.addLayout(brand_stack)
        layout.addWidget(self.camera_combo)
        layout.addWidget(self.btn_30fps_boost)
        layout.addWidget(self.btn_driver_settings)

        layout.addStretch(1)

        # Center: Recessed LCD Digital Telemetry Screen (#08080B inset panel with 1px solid #262632 bezel)
        self.lcd_frame = QFrame(bar)
        self.lcd_frame.setObjectName("RecessedLCDPanel")
        self.lcd_frame.setFixedHeight(34)
        lcd_layout = QHBoxLayout(self.lcd_frame)
        lcd_layout.setContentsMargins(12, 0, 12, 0)

        self.status_pill = QLabel("720P MJPG | FPS: 30.0 | SHUTTER: -4 EV | ISO/GAIN: 130 | SYNC: 1.0X CFR")
        self.status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_pill.setStyleSheet(
            'color: #10B981; font-family: "Consolas", "JetBrains Mono", monospace; font-size: 11px; font-weight: 700;'
        )
        lcd_layout.addWidget(self.status_pill)
        layout.addWidget(self.lcd_frame)

        layout.addStretch(1)

        # Right Cluster: PURE VIEW, SYNC GITHUB, RESET, GALLERY
        self.btn_pure_view = TactileHardwareButton(
            "PURE VIEW",
            led_color="amber",
            checkable=True,
            checked=False,
            parent=bar,
        )
        self.btn_pure_view.setFixedSize(98, 32)

        self.btn_sync_github = TactileHardwareButton(
            "SYNC GITHUB",
            led_color="emerald",
            checkable=False,
            parent=bar,
        )
        self.btn_sync_github.setFixedSize(112, 32)
        self.btn_sync_github.setToolTip("Fetch & Pull latest updates from GitHub and hot-restart.")

        self.btn_reset_all = TactileHardwareButton(
            "RESET",
            led_color="none",
            checkable=False,
            parent=bar,
        )
        self.btn_reset_all.setFixedSize(68, 32)

        self.btn_gallery = TactileHardwareButton(
            "GALLERY",
            led_color="none",
            checkable=False,
            parent=bar,
        )
        self.btn_gallery.setFixedSize(80, 32)

        layout.addWidget(self.btn_pure_view)
        layout.addWidget(self.btn_sync_github)
        layout.addWidget(self.btn_reset_all)
        layout.addWidget(self.btn_gallery)

        return bar

    def _build_bottom_evf_glass_bar(self) -> QFrame:
        bar = QFrame(self)
        bar.setObjectName("BottomCaptureBar")
        bar.setFixedHeight(74)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(12)

        # Left: Live compact Audio VU Peak Meter (-60dB to 0dB LED segments) + 50Hz Anti-Flicker Status
        self.vu_meter_widget = AudioVUPeakMeterWidget(bar)
        layout.addWidget(self.vu_meter_widget)

        layout.addStretch(1)

        # Center: Tactile Transport Controls — [ Timer ] [ Softbox Flash ] [ 60px 3D SHUTTER ] [ 60px 3D RECORD ] [ Pause ] [ Burst 3x ]
        self.combo_timer = QComboBox(bar)
        self.combo_timer.setFixedSize(96, 34)
        self.combo_timer.addItems(["Timer: Off", "Timer: 3s", "Timer: 5s", "Timer: 10s"])

        self.btn_flash = TactileHardwareButton(
            "Softbox Flash",
            led_color="amber",
            checkable=True,
            checked=False,
            parent=bar,
        )
        self.btn_flash.setFixedSize(112, 34)

        self.btn_shutter = MechanicalShutterButton(bar)
        self.btn_record = CinemaRecordButton(bar)

        self.btn_pause_rec = TactileHardwareButton(
            "Pause",
            led_color="amber",
            checkable=True,
            checked=False,
            parent=bar,
        )
        self.btn_pause_rec.setFixedSize(72, 34)
        self.btn_pause_rec.setEnabled(False)

        self.btn_burst = TactileHardwareButton(
            "Burst 3x",
            led_color="none",
            checkable=False,
            parent=bar,
        )
        self.btn_burst.setFixedSize(78, 34)

        self.lbl_rec_timer = QLabel("00:00:00:00", bar)
        self.lbl_rec_timer.setFixedSize(94, 30)
        self.lbl_rec_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rec_timer.setStyleSheet(
            "background-color: #281117; border: 1px solid #E11D48; border-radius: 4px; "
            'color: #F4F4F6; font-family: "Consolas", monospace; font-size: 11px; font-weight: 700;'
        )
        self.lbl_rec_timer.setVisible(False)

        layout.addWidget(self.combo_timer)
        layout.addWidget(self.btn_flash)
        layout.addWidget(self.btn_shutter)
        layout.addWidget(self.btn_record)
        layout.addWidget(self.lbl_rec_timer)
        layout.addWidget(self.btn_pause_rec)
        layout.addWidget(self.btn_burst)

        layout.addStretch(1)

        # Right: [ Virtual Cam LED Toggle ] [ 16:9 / 9:16 Aspect ]
        self.btn_vcam = TactileHardwareButton(
            "Virtual Cam",
            led_color="emerald",
            checkable=True,
            checked=False,
            parent=bar,
        )
        self.btn_vcam.setFixedSize(110, 34)

        self.btn_aspect = TactileHardwareButton(
            "16:9 Wide",
            led_color="amber",
            checkable=True,
            checked=False,
            parent=bar,
        )
        self.btn_aspect.setFixedSize(86, 34)

        layout.addWidget(self.btn_vcam)
        layout.addWidget(self.btn_aspect)

        return bar

    def _build_right_control_deck(self) -> QFrame:
        sidebar = QFrame(self)
        sidebar.setObjectName("RightStudioSidebar")
        sidebar.setFixedWidth(370)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top 4 3D Interlocking Mode Selector Buttons (Height: 40px)
        tab_header = QWidget(sidebar)
        tab_header.setStyleSheet("background-color: #0B0B10; border-bottom: 1px solid #242430;")
        tab_header_layout = QVBoxLayout(tab_header)
        tab_header_layout.setContentsMargins(8, 8, 8, 8)
        self.sidebar_tabs = SegmentedBar(
            ["1. EXP/LIGHT", "2. COLOR/LUT", "3. OPTICS/AI", "4. PRESETS(12)"],
            height=40,
        )
        tab_header_layout.addWidget(self.sidebar_tabs)
        layout.addWidget(tab_header)

        self.sidebar_stack = QStackedWidget(sidebar)
        self.sidebar_stack.addWidget(self._build_mode_1_exposure_light())
        self.sidebar_stack.addWidget(self._build_mode_2_color_luts())
        self.sidebar_stack.addWidget(self._build_mode_3_optics_ai())
        self.sidebar_stack.addWidget(self._build_mode_4_presets())

        layout.addWidget(self.sidebar_stack, 1)
        return sidebar

    def _build_mode_1_exposure_light(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(14, 14, 14, 14)
        vbox.setSpacing(12)

        # Card 1: LIGHTING & CLARITY
        c1 = InspectorCard("LIGHTING && CLARITY")
        self.sl_light_boost = MachinedFaderSlider(
            "Smart Room Light Boost (Shadow Lift)", 0, 100, 25, step=1, decimals=0, suffix="%"
        )
        self.sl_brightness = MachinedFaderSlider(
            "Digital Brightness", -100, 100, 0, step=1, decimals=0, bipolar=True
        )
        self.sl_contrast = MachinedFaderSlider(
            "Micro-Contrast", -100, 100, 0, step=1, decimals=0, bipolar=True
        )
        self.sl_sharpness = MachinedFaderSlider(
            "Optical Sharpness (HD Crisp)", 0, 100, 15, step=1, decimals=0, suffix="%"
        )
        self.sl_denoise = MachinedFaderSlider(
            "Low-Light Denoise", 0, 100, 0, step=1, decimals=0, suffix="%"
        )

        for sl in (
            self.sl_light_boost,
            self.sl_brightness,
            self.sl_contrast,
            self.sl_sharpness,
            self.sl_denoise,
        ):
            c1.add_widget(sl)
        vbox.addWidget(c1)

        # Card 2: C270 SENSOR HARDWARE — EXACT NATIVE RANGES
        c2 = InspectorCard("C270 SENSOR HARDWARE (NATIVE RANGES)")
        self.sw_unlock_30fps = ToggleSwitch("Unlock 30 FPS (Disable Low-Light Lag)", checked=True)
        self.sl_hw_exp = MachinedFaderSlider(
            "Sensor Shutter (Exposure)", -11, -2, -4, step=1, decimals=0, suffix=" EV"
        )
        self.sl_hw_gain = MachinedFaderSlider(
            "Sensor ISO Gain", 0, 255, 130, step=1, decimals=0
        )
        self.sl_hw_contrast = MachinedFaderSlider(
            "Hardware Contrast (Native=32)", 0, 255, 32, step=1, decimals=0
        )
        self.sl_hw_saturation = MachinedFaderSlider(
            "Hardware Saturation (Native=32)", 0, 255, 32, step=1, decimals=0
        )
        self.btn_restore_hw_defaults = TactileHardwareButton(
            "Restore Factory C270 Hardware Defaults",
            led_color="amber",
            checkable=False,
        )
        self.btn_restore_hw_defaults.setFixedHeight(34)

        c2.add_widget(self.sw_unlock_30fps)
        c2.add_widget(self.sl_hw_exp)
        c2.add_widget(self.sl_hw_gain)
        c2.add_widget(self.sl_hw_contrast)
        c2.add_widget(self.sl_hw_saturation)
        c2.add_widget(self.btn_restore_hw_defaults)
        vbox.addWidget(c2)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_mode_2_color_luts(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(14, 14, 14, 14)
        vbox.setSpacing(12)

        # Card 1: CINEMA FILM LOOKS (8 Tactile 3D Buttons in a 2x4 grid with LED indicator)
        c1 = InspectorCard("CINEMA FILM LOOKS (8 PROFILES)")
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, look_name in enumerate(STUDIO_LOOK_NAMES):
            btn = TactileHardwareButton(
                look_name,
                led_color="amber",
                checkable=True,
                checked=(look_name == "Pure Natural (Off)"),
            )
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, n=look_name: self._on_look_selected(n))
            self._look_buttons[look_name] = btn
            grid.addWidget(btn, i // 2, i % 2)
        c1.add_layout(grid)

        self.sl_look_intensity = MachinedFaderSlider(
            "Look Intensity", 0, 100, 75, step=1, decimals=0, suffix="%"
        )
        self.btn_load_cube = TactileHardwareButton(
            "Load Custom .CUBE 3D LUT...",
            led_color="none",
            checkable=False,
        )
        self.btn_load_cube.setFixedHeight(32)

        c1.add_widget(self.sl_look_intensity)
        c1.add_widget(self.btn_load_cube)
        vbox.addWidget(c1)

        # Card 2: WHITE BALANCE & TONE
        c2 = InspectorCard("WHITE BALANCE && TONE")
        self.sl_warmth = MachinedFaderSlider(
            "Color Temperature (Warmth)", -100, 100, 0, step=1, decimals=0, bipolar=True
        )
        self.sl_tint = MachinedFaderSlider(
            "Tint (Green / Magenta)", -100, 100, 0, step=1, decimals=0, bipolar=True
        )
        self.sl_saturation = MachinedFaderSlider(
            "Vibrance (Rich Color)", -100, 100, 0, step=1, decimals=0, bipolar=True
        )
        self.sl_vignette = MachinedFaderSlider(
            "Optical Lens Vignette", 0, 100, 0, step=1, decimals=0, suffix="%"
        )

        for sl in (self.sl_warmth, self.sl_tint, self.sl_saturation, self.sl_vignette):
            c2.add_widget(sl)
        vbox.addWidget(c2)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_mode_3_optics_ai(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(14, 14, 14, 14)
        vbox.setSpacing(12)

        # Card 1: FLUID GIMBAL PTZ & GEOMETRY
        c1 = InspectorCard("FLUID GIMBAL PTZ && GEOMETRY")
        self.sl_zoom = MachinedFaderSlider(
            "Optical-Feel Zoom", 1.00, 3.00, 1.00, step=0.02, decimals=2, suffix="x"
        )
        self.sl_pan_x = MachinedFaderSlider(
            "Pan X (Horizontal)", -1.00, 1.00, 0.00, step=0.02, decimals=2, bipolar=True
        )
        self.sl_tilt_y = MachinedFaderSlider(
            "Tilt Y (Vertical)", -1.00, 1.00, 0.00, step=0.02, decimals=2, bipolar=True
        )

        geom_grid = QGridLayout()
        geom_grid.setSpacing(6)
        self.btn_mirror = TactileHardwareButton("Mirror Video", led_color="amber", checkable=True, checked=True)
        self.btn_flip_v = TactileHardwareButton("Flip V", led_color="amber", checkable=True, checked=False)
        self.btn_rotate = TactileHardwareButton("Rotate 90°", led_color="none", checkable=False)
        self.btn_center_frame = TactileHardwareButton("Center Reset", led_color="none", checkable=False)

        for b in (self.btn_mirror, self.btn_flip_v, self.btn_rotate, self.btn_center_frame):
            b.setFixedHeight(32)

        geom_grid.addWidget(self.btn_mirror, 0, 0)
        geom_grid.addWidget(self.btn_flip_v, 0, 1)
        geom_grid.addWidget(self.btn_rotate, 1, 0)
        geom_grid.addWidget(self.btn_center_frame, 1, 1)

        c1.add_widget(self.sl_zoom)
        c1.add_widget(self.sl_pan_x)
        c1.add_widget(self.sl_tilt_y)
        c1.add_layout(geom_grid)
        vbox.addWidget(c1)

        # Card 2: AI PORTRAIT STUDIO
        c2 = InspectorCard("AI PORTRAIT STUDIO")
        self.combo_bg_mode = QComboBox()
        self.combo_bg_mode.setFixedHeight(32)
        self.combo_bg_mode.addItems(
            [
                "Off (Natural)",
                "Optical Bokeh Blur",
                "Studio Dimmed Spotlight",
                "Custom Backdrop",
            ]
        )
        self.sl_bg_strength = MachinedFaderSlider(
            "Blur / Dim Strength", 10, 100, 50, step=1, decimals=0, suffix="%"
        )
        self.sw_auto_frame = ToggleSwitch("AI Face Auto-Framing (Center Stage)", checked=False)
        self.sl_skin_softening = MachinedFaderSlider(
            "Portrait Skin Softening", 0, 100, 0, step=1, decimals=0, suffix="%"
        )

        c2.add_widget(self.combo_bg_mode)
        c2.add_widget(self.sl_bg_strength)
        c2.add_widget(self.sw_auto_frame)
        c2.add_widget(self.sl_skin_softening)
        vbox.addWidget(c2)

        # Card 3: VIEWFINDER GUIDES & BROADCAST
        c3 = InspectorCard("VIEWFINDER GUIDES && BROADCAST")
        self.sw_grid = ToggleSwitch("Rule of Thirds Grid", checked=False)
        self.sw_cinema_bars = ToggleSwitch("2.35:1 Cinema Scope Bars", checked=False)
        self.sw_corner_hud = ToggleSwitch("Show Corner RGB Histogram", checked=False)
        self.sw_lower_third = ToggleSwitch("Show Lower-Third Name Tag", checked=False)

        self.ed_lt_name = QLineEdit("Alex Morgan")
        self.ed_lt_name.setPlaceholderText("Broadcast Speaker Name")
        self.ed_lt_title = QLineEdit("Cinema Systems Architect")
        self.ed_lt_title.setPlaceholderText("Speaker Role / Title")

        c3.add_widget(self.sw_grid)
        c3.add_widget(self.sw_cinema_bars)
        c3.add_widget(self.sw_corner_hud)
        c3.add_widget(self.sw_lower_third)
        c3.add_widget(self.ed_lt_name)
        c3.add_widget(self.ed_lt_title)
        vbox.addWidget(c3)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_mode_4_presets(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(14, 14, 14, 14)
        vbox.setSpacing(12)

        # Card 1: 12 ONE-CLICK STUDIO PRESETS (2-Column Grid with LED Active Indicator)
        c1 = InspectorCard("12 ONE-CLICK STUDIO PRESETS")
        preset_grid = QGridLayout()
        preset_grid.setSpacing(6)
        factory_names = list(FACTORY_PRESETS.keys())
        for idx, pname in enumerate(factory_names):
            btn = TactileHardwareButton(
                pname,
                led_color="amber",
                checkable=True,
                checked=(idx == 0),
            )
            btn.setFixedHeight(36)
            btn.setToolTip(PRESET_DESCRIPTIONS.get(pname, pname))
            btn.clicked.connect(lambda checked, n=pname: self._on_preset_selected(n))
            self._preset_buttons[pname] = btn
            preset_grid.addWidget(btn, idx // 2, idx % 2)
        c1.add_layout(preset_grid)
        vbox.addWidget(c1)

        # Card 2: CUSTOM USER PRESETS & JSON IMPORT/EXPORT
        c2 = InspectorCard("CUSTOM USER PRESET BANK")
        self.combo_preset = QComboBox()
        self.combo_preset.setFixedHeight(32)
        self._reload_preset_combo()

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.btn_save_preset = TactileHardwareButton("Save New Preset", led_color="none")
        self.btn_save_preset.setFixedHeight(32)
        self.btn_del_preset = TactileHardwareButton("Delete Selected", led_color="none")
        self.btn_del_preset.setFixedHeight(32)
        row1.addWidget(self.btn_save_preset)
        row1.addWidget(self.btn_del_preset)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.btn_export_json = TactileHardwareButton("Export JSON", led_color="none")
        self.btn_export_json.setFixedHeight(32)
        self.btn_import_json = TactileHardwareButton("Import JSON", led_color="none")
        self.btn_import_json.setFixedHeight(32)
        row2.addWidget(self.btn_export_json)
        row2.addWidget(self.btn_import_json)

        c2.add_widget(self.combo_preset)
        c2.add_layout(row1)
        c2.add_layout(row2)
        vbox.addWidget(c2)

        # Card 3: OUTPUT RESOLUTION & STILL ENCODING
        c3 = InspectorCard("MASTER OUTPUT PIPELINE")
        self.seg_res = SegmentedBar(["720p 30FPS Native", "1080p Lanczos4"], height=34)
        self.seg_fmt = SegmentedBar(["PNG (Lossless)", "JPG (98% Master)"], height=34)
        c3.add_widget(self.seg_res)
        c3.add_widget(self.seg_fmt)
        vbox.addWidget(c3)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _connect_signals(self) -> None:
        # Top Telemetry Deck
        self.camera_combo.currentIndexChanged.connect(self._on_device_changed)
        self.btn_30fps_boost.toggled.connect(self._on_top_30fps_boost_toggled)
        self.btn_driver_settings.clicked.connect(self.camera_worker.request_driver_settings_dialog)
        self.btn_pure_view.toggled.connect(lambda v: self._set_param("pure_view_bypass", v))
        self.btn_sync_github.clicked.connect(self._on_sync_github_clicked)
        self.btn_reset_all.clicked.connect(self._on_reset_all)
        self.btn_gallery.clicked.connect(self._on_open_gallery)

        # GitHub Auto-Sync signals
        self.github_sync.sync_status.connect(self._on_github_status)
        self.github_sync.sync_completed.connect(self._on_github_sync_completed)

        # Sidebar Mode Tabs
        self.sidebar_tabs.indexChanged.connect(self.sidebar_stack.setCurrentIndex)

        # Mode 1: Exposure & Light
        self.sl_light_boost.valueChanged.connect(lambda v: self._set_param("light_boost", v))
        self.sl_brightness.valueChanged.connect(lambda v: self._set_param("brightness", v))
        self.sl_contrast.valueChanged.connect(lambda v: self._set_param("contrast", v))
        self.sl_sharpness.valueChanged.connect(lambda v: self._set_param("sharpness", v))
        self.sl_denoise.valueChanged.connect(lambda v: self._set_param("denoise", v))

        self.sw_unlock_30fps.toggled.connect(self._on_sidebar_30fps_toggled)
        self.sl_hw_exp.valueChanged.connect(lambda v: self._set_param("hardware_exposure", v))
        self.sl_hw_gain.valueChanged.connect(lambda v: self._set_param("hardware_gain", v))
        self.sl_hw_contrast.valueChanged.connect(lambda v: self._set_param("hw_contrast", v))
        self.sl_hw_saturation.valueChanged.connect(lambda v: self._set_param("hw_saturation", v))
        self.btn_restore_hw_defaults.clicked.connect(self._on_restore_hw_defaults)

        # Mode 2: Color & LUTs
        self.sl_look_intensity.valueChanged.connect(lambda v: self._set_param("look_intensity", v))
        self.btn_load_cube.clicked.connect(self._on_load_custom_cube)
        self.sl_warmth.valueChanged.connect(lambda v: self._set_param("warmth", v))
        self.sl_tint.valueChanged.connect(lambda v: self._set_param("tint", v))
        self.sl_saturation.valueChanged.connect(lambda v: self._set_param("saturation", v))
        self.sl_vignette.valueChanged.connect(lambda v: self._set_param("vignette", v))

        # Mode 3: Optics & AI
        self.sl_zoom.valueChanged.connect(self._on_zoom_slider_changed)
        self.sl_pan_x.valueChanged.connect(lambda v: self._on_pan_tilt_slider_changed("pan_x", v))
        self.sl_tilt_y.valueChanged.connect(lambda v: self._on_pan_tilt_slider_changed("tilt_y", v))
        self.btn_mirror.toggled.connect(lambda v: self._set_param("mirror_h", v))
        self.btn_flip_v.toggled.connect(lambda v: self._set_param("flip_v", v))
        self.btn_rotate.clicked.connect(self._on_rotate_clicked)
        self.btn_center_frame.clicked.connect(self._on_reset_ptz)

        self.combo_bg_mode.currentTextChanged.connect(lambda t: self._set_param("bg_mode", t))
        self.sl_bg_strength.valueChanged.connect(lambda v: self._set_param("bg_strength", v))
        self.sw_auto_frame.toggled.connect(lambda v: self._set_param("auto_frame_face", v))
        self.sl_skin_softening.valueChanged.connect(lambda v: self._set_param("skin_softening", v))

        self.sw_grid.toggled.connect(self._on_viewport_guides_changed)
        self.sw_cinema_bars.toggled.connect(self._on_viewport_guides_changed)
        self.sw_corner_hud.toggled.connect(self._on_corner_hud_toggled)
        self.sw_lower_third.toggled.connect(lambda v: self._set_param("show_lower_third", v))
        self.ed_lt_name.textChanged.connect(lambda t: self._set_param("lower_third_name", t))
        self.ed_lt_title.textChanged.connect(lambda t: self._set_param("lower_third_title", t))

        # Mode 4: Presets & Output
        self.combo_preset.currentTextChanged.connect(self._on_preset_selected)
        self.btn_save_preset.clicked.connect(self._on_save_preset)
        self.btn_del_preset.clicked.connect(self._on_delete_preset)
        self.btn_export_json.clicked.connect(self._on_export_presets)
        self.btn_import_json.clicked.connect(self._on_import_presets)
        self.seg_res.indexChanged.connect(lambda idx: self._set_param("upscale_1080p", idx == 1))
        self.seg_fmt.indexChanged.connect(
            lambda idx: self._set_param("photo_format", "JPG (98% Master)" if idx == 1 else "PNG (Lossless)")
        )

        # Viewport Interactive PTZ
        self.viewport.ptz_changed.connect(self._on_viewport_ptz_dragged)
        self.viewport.ptz_reset_requested.connect(self._on_reset_ptz)
        self.viewport.flash_peak_reached.connect(self._execute_immediate_snapshot)

        # Bottom EVF Transport Bar
        self.btn_shutter.clicked.connect(self._on_shutter_clicked)
        self.btn_record.clicked.connect(self._on_record_clicked)
        self.btn_pause_rec.clicked.connect(self.recorder.toggle_pause)
        self.btn_burst.clicked.connect(self._on_burst_clicked)
        self.btn_vcam.toggled.connect(self._on_vcam_toggled)
        self.btn_aspect.toggled.connect(self._on_aspect_toggled)

        # Worker & Audio Signals
        self.camera_worker.frame_ready.connect(self._on_frame_ready)
        self.audio_monitor.levels_updated.connect(self.viewport.set_audio_levels)
        self.audio_monitor.levels_updated.connect(self.vu_meter_widget.set_levels)
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

    def _on_top_30fps_boost_toggled(self, checked: bool) -> None:
        self.btn_30fps_boost.setText("30-FPS BOOST: ON" if checked else "30-FPS BOOST: OFF")
        if self._updating_ui:
            return
        self._updating_ui = True
        self.sw_unlock_30fps.setChecked(checked)
        if checked and self.sl_light_boost.value() < 5.0:
            self.sl_light_boost.setValue(25.0)
            self.camera_worker.update_param("light_boost", 25.0)
        self._updating_ui = False
        self.camera_worker.update_param("unlock_30fps", checked)

    def _on_sidebar_30fps_toggled(self, checked: bool) -> None:
        if self._updating_ui:
            return
        self._updating_ui = True
        self.btn_30fps_boost.setChecked(checked)
        self.btn_30fps_boost.setText("30-FPS BOOST: ON" if checked else "30-FPS BOOST: OFF")
        if checked and self.sl_light_boost.value() < 5.0:
            self.sl_light_boost.setValue(25.0)
            self.camera_worker.update_param("light_boost", 25.0)
        self._updating_ui = False
        self.camera_worker.update_param("unlock_30fps", checked)

    def _on_restore_hw_defaults(self) -> None:
        updated = self.camera_worker.restore_native_c270_defaults()
        self._apply_params_to_ui(updated)

    def _on_look_selected(self, look_name: str) -> None:
        for name, btn in self._look_buttons.items():
            btn.setChecked(name == look_name)
        self._set_param("active_lut", look_name)

    def _on_load_custom_cube(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select .CUBE 3D/1D LUT File",
            str(self.output_dir),
            "CUBE LUT Files (*.cube *.CUBE);;All Files (*)",
        )
        if file_path:
            self._set_param("custom_cube_path", file_path)
            self.btn_load_cube.setText(f"LUT: {Path(file_path).name[:18]}")

    def _on_zoom_slider_changed(self, val: float) -> None:
        if self._updating_ui:
            return
        params = self.camera_worker.get_params_copy()
        self.viewport.set_ptz_targets(val, float(params.get("pan_x", 0.0)), float(params.get("tilt_y", 0.0)))
        self.camera_worker.update_param("digital_zoom", val)

    def _on_pan_tilt_slider_changed(self, key: str, val: float) -> None:
        if self._updating_ui:
            return
        self.camera_worker.update_param(key, val)
        params = self.camera_worker.get_params_copy()
        self.viewport.set_ptz_targets(
            float(params.get("digital_zoom", 1.0)),
            float(params.get("pan_x", 0.0)),
            float(params.get("tilt_y", 0.0)),
        )

    def _on_viewport_ptz_dragged(self, z: float, px: float, py: float) -> None:
        self._updating_ui = True
        self.sl_zoom.setValue(z)
        self.sl_pan_x.setValue(px)
        self.sl_tilt_y.setValue(py)
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
        self.sl_pan_x.setValue(0.00)
        self.sl_tilt_y.setValue(0.00)
        self._updating_ui = False
        self.viewport.set_ptz_targets(1.00, 0.00, 0.00)
        self.camera_worker.update_param("digital_zoom", 1.00)
        self.camera_worker.update_param("pan_x", 0.00)
        self.camera_worker.update_param("tilt_y", 0.00)
        self.camera_worker.update_param("rotate_quadrant", 0)

    def _on_viewport_guides_changed(self) -> None:
        self.viewport.show_grid = self.sw_grid.isChecked()
        self.viewport.show_cinema_bars = self.sw_cinema_bars.isChecked()
        self._set_param("show_grid", self.sw_grid.isChecked())
        self._set_param("show_cinema_bars", self.sw_cinema_bars.isChecked())
        self.viewport.update()

    def _on_corner_hud_toggled(self, checked: bool) -> None:
        self.viewport.show_corner_hud = checked
        self._set_param("show_corner_hud", checked)
        self.viewport.update()

    def _on_aspect_toggled(self, checked: bool) -> None:
        mode = "9:16" if checked else "16:9"
        self.btn_aspect.setText("9:16 Vert" if checked else "16:9 Wide")
        self.viewport.set_aspect_mode(mode)
        self._set_param("aspect_mode", mode)

    def _on_frame_ready(self, frame_bgr, telemetry: Dict[str, Any]) -> None:
        self.viewport.update_frame(frame_bgr, telemetry)
        res_label = "1080P LANCZOS" if telemetry.get("upscaled", False) else "720P MJPG"
        fps = float(telemetry.get("fps", 30.0))
        ev = int(telemetry.get("exposure_ev", -4))
        iso = int(telemetry.get("gain_iso", 130))
        self.status_pill.setText(
            f"{res_label} | FPS: {fps:4.1f} | SHUTTER: {ev} EV | ISO/GAIN: {iso} | SYNC: 1.0X CFR"
        )

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
            unlock = bool(params.get("unlock_30fps", True))
            self.btn_30fps_boost.setChecked(unlock)
            self.btn_30fps_boost.setText("30-FPS BOOST: ON" if unlock else "30-FPS BOOST: OFF")
            self.sw_unlock_30fps.setChecked(unlock)

            self.sl_light_boost.setValue(float(params.get("light_boost", 25.0)))
            self.sl_brightness.setValue(float(params.get("brightness", 0.0)))
            self.sl_contrast.setValue(float(params.get("contrast", 0.0)))
            self.sl_sharpness.setValue(float(params.get("sharpness", 15.0)))
            self.sl_denoise.setValue(float(params.get("denoise", 0.0)))

            self.sl_hw_exp.setValue(float(params.get("hardware_exposure", -4.0)))
            self.sl_hw_gain.setValue(float(params.get("hardware_gain", 130.0)))
            self.sl_hw_contrast.setValue(float(params.get("hw_contrast", 32.0)))
            self.sl_hw_saturation.setValue(float(params.get("hw_saturation", 32.0)))

            look = str(params.get("active_lut", "Pure Natural (Off)"))
            for name, btn in self._look_buttons.items():
                btn.setChecked(name == look)
            self.sl_look_intensity.setValue(float(params.get("look_intensity", 75.0)))
            self.sl_warmth.setValue(float(params.get("warmth", 0.0)))
            self.sl_tint.setValue(float(params.get("tint", 0.0)))
            self.sl_saturation.setValue(float(params.get("saturation", 0.0)))
            self.sl_vignette.setValue(float(params.get("vignette", 0.0)))

            self.sl_zoom.setValue(float(params.get("digital_zoom", 1.00)))
            self.sl_pan_x.setValue(float(params.get("pan_x", 0.00)))
            self.sl_tilt_y.setValue(float(params.get("tilt_y", 0.00)))
            self.btn_mirror.setChecked(bool(params.get("mirror_h", True)))
            self.btn_flip_v.setChecked(bool(params.get("flip_v", False)))
            self.combo_bg_mode.setCurrentText(str(params.get("bg_mode", "Off (Natural)")))
            self.sl_bg_strength.setValue(float(params.get("bg_strength", 50.0)))
            self.sw_auto_frame.setChecked(bool(params.get("auto_frame_face", False)))
            self.sl_skin_softening.setValue(float(params.get("skin_softening", 0.0)))

            self.sw_grid.setChecked(bool(params.get("show_grid", False)))
            self.sw_cinema_bars.setChecked(bool(params.get("show_cinema_bars", False)))
            self.sw_corner_hud.setChecked(bool(params.get("show_corner_hud", False)))
            self.sw_lower_third.setChecked(bool(params.get("show_lower_third", False)))
            self.ed_lt_name.setText(str(params.get("lower_third_name", "Alex Morgan")))
            self.ed_lt_title.setText(str(params.get("lower_third_title", "Cinema Systems Architect")))

            active_preset = str(params.get("active_preset_name", "01. Pure Natural 30FPS"))
            for pname, pbtn in self._preset_buttons.items():
                pbtn.setChecked(pname == active_preset)
            self.combo_preset.setCurrentText(active_preset)

            self.seg_res.set_current_index(1 if params.get("upscale_1080p", False) else 0)
            self.seg_fmt.set_current_index(1 if "JPG" in str(params.get("photo_format", "")) else 0)

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
        name, ok = QInputDialog.getText(self, "Save Custom Studio Preset", "Preset Name:", text="My Cinema Grade")
        if ok and name.strip():
            self.preset_manager.save_user_preset(name.strip(), self.camera_worker.get_params_copy())
            self._reload_preset_combo(select_name=name.strip())

    def _on_delete_preset(self) -> None:
        cur = self.combo_preset.currentText()
        if self.preset_manager.delete_user_preset(cur):
            self._reload_preset_combo()
        else:
            QMessageBox.information(self, "Factory Preset Protected", "The 12 built-in studio presets cannot be deleted.")

    def _on_export_presets(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Studio Presets to JSON",
            str(self.output_dir / "lumixa_custom_presets.json"),
            "JSON Files (*.json)",
        )
        if file_path:
            self.preset_manager.export_presets_json(Path(file_path))

    def _on_import_presets(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Studio Presets from JSON",
            str(self.output_dir),
            "JSON Files (*.json)",
        )
        if file_path:
            count = self.preset_manager.import_presets_json(Path(file_path))
            self._reload_preset_combo()
            QMessageBox.information(self, "Presets Imported", f"Imported {count} preset(s) into bank.")

    def _on_reset_all(self) -> None:
        self._apply_params_to_ui(DEFAULT_STUDIO_PARAMS)

    def _on_sync_github_clicked(self) -> None:
        self.btn_sync_github.setText("SYNCING...")
        self.github_sync.trigger_pull_and_sync_async()

    def _on_github_status(self, msg: str, update_available: bool) -> None:
        if update_available:
            self.btn_sync_github.setText("UPDATE READY")
        else:
            self.btn_sync_github.setText("SYNC GITHUB")
        self.btn_sync_github.setToolTip(msg)

    def _on_github_sync_completed(self, success: bool, detail: str) -> None:
        self.btn_sync_github.setText("SYNC GITHUB")
        if success:
            ans = QMessageBox.question(
                self,
                "LUMIXA PRO — GitHub Cloud Sync Complete",
                f"Repository synchronized with GitHub:\n{detail}\n\nHot-restart application now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            QMessageBox.information(self, "GitHub Cloud Sync", f"Sync status: {detail}")

    def _on_shutter_clicked(self) -> None:
        t = self.combo_timer.currentText()
        if "3s" in t:
            self._start_countdown(3)
        elif "5s" in t:
            self._start_countdown(5)
        elif "10s" in t:
            self._start_countdown(10)
        else:
            self._trigger_flash_or_snapshot()

    def _on_burst_clicked(self) -> None:
        params = self.camera_worker.get_params_copy()
        self.camera_worker.trigger_snapshot(fmt=str(params.get("photo_format", "PNG (Lossless)")), count=3)

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
        self.btn_pause_rec.setEnabled(is_recording)
        self.btn_pause_rec.setChecked(is_paused)
        self.btn_pause_rec.setText("Resume" if is_paused else "Pause")
        self.lbl_rec_timer.setVisible(is_recording)
        self.viewport.set_tally_state(is_recording, self.virtual_cam.is_active)

    def _on_vcam_toggled(self, checked: bool) -> None:
        params = self.camera_worker.get_params_copy()
        w, h = (1920, 1080) if params.get("upscale_1080p", False) else (1280, 720)
        ok = self.virtual_cam.set_enabled(checked, width=w, height=h)
        if checked and not ok:
            self.btn_vcam.blockSignals(True)
            self.btn_vcam.setChecked(False)
            self.btn_vcam.blockSignals(False)

    def _on_vcam_status(self, active: bool, msg: str) -> None:
        self.btn_vcam.setToolTip(msg)
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
