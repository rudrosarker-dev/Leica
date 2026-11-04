# -*- coding: utf-8 -*-
"""
5-Zone "Obsidian Leica Matte" Main Studio Window (`ui/main_window.py`).
Connects:
- Zone A: Top Telemetry & Hardware Bar (Fixed Height: 46px)
- Zone B: Left Dock Inspector: Hardware UVC & Optical ISP (Fixed Width: 320px)
- Zone C: Center Cinema Viewport & Interactive HUD (Expanding)
- Zone D: Right Dock Inspector: Color Grading, AI Studio & Broadcast Overlays (Fixed Width: 340px)
- Zone E: Bottom Transport, Capture & Preset Deck (Fixed Height: 76px)
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen
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
    QFileDialog,
    QColorDialog,
    QInputDialog,
    QMessageBox,
)

from core.camera_engine import CameraWorker
from core.color_lut import FILM_LOOK_NAMES
from core.preset_manager import PresetManager, DEFAULT_STUDIO_PARAMS
from core.recorder_audio import AudioVUMonitor, StudioRecorder, VirtualCamManager
from ui.viewport_hud import ViewportCanvas
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


class TallyDotWidget(QWidget):
    """10x10px live recording indicator dot (#3F3F46 idle, blinking #E11D48 every 500ms when recording)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._recording = False
        self._blink_on = True
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._toggle_blink)

    def set_recording(self, active: bool) -> None:
        self._recording = bool(active)
        if self._recording:
            self._blink_on = True
            self._timer.start()
        else:
            self._timer.stop()
            self._blink_on = False
        self.update()

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        col = QColor("#E11D48") if (self._recording and self._blink_on) else QColor("#3F3F46")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(col)
        painter.drawEllipse(QPointF(self.width() * 0.5, self.height() * 0.5), 5.0, 5.0)
        painter.end()


class FilmLookButton(QPushButton):
    """2x3 Grid Film Look button with painted #E5A93C active indicator dot."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#E5A93C"))
            painter.drawEllipse(QPointF(10.0, self.height() * 0.5), 3.0, 3.0)
            painter.end()


class MainWindow(QMainWindow):
    """Main 5-Zone Studio Window for LEICA // C270 OPTIX STUDIO."""

    def __init__(self, output_dir: Path) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.setWindowTitle("LEICA // C270 OPTIX STUDIO")
        self.resize(1480, 880)
        self.setMinimumSize(1240, 740)

        # Core Managers & Threads
        self.preset_manager = PresetManager(self.output_dir)
        self.audio_monitor = AudioVUMonitor(self)
        self.recorder = StudioRecorder(self.output_dir, self.audio_monitor, self)
        self.virtual_cam = VirtualCamManager(self)
        self.camera_worker = CameraWorker(self.output_dir, self)
        self.camera_worker.recorder_hook = self.recorder
        self.camera_worker.virtual_cam_hook = self.virtual_cam

        # Countdown Timer for Timed Shutter Release
        self._countdown_remaining = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self._updating_ui = False
        self._film_look_buttons: Dict[str, FilmLookButton] = {}

        # Build 5-Zone UI
        self._build_ui()
        self._connect_signals()

        # Populate devices & start engines
        self._refresh_camera_devices()
        self.audio_monitor.start()
        self.camera_worker.start(CameraWorker.Priority.HighPriority)

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. ZONE A — Top Telemetry & Hardware Bar (46px)
        root_layout.addWidget(self._build_zone_a_top_bar())

        # 2. MIDDLE WORKSPACE (Zone B + Zone C + Zone D)
        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        middle_layout.addWidget(self._build_zone_b_left_dock())
        self.viewport = ViewportCanvas(self)
        middle_layout.addWidget(self.viewport, 1)
        middle_layout.addWidget(self._build_zone_d_right_dock())

        root_layout.addLayout(middle_layout, 1)

        # 3. ZONE E — Bottom Transport, Capture & Preset Deck (76px)
        root_layout.addWidget(self._build_zone_e_bottom_deck())

    def _build_zone_a_top_bar(self) -> QFrame:
        bar = QFrame(self)
        bar.setObjectName("TopTelemetryBar")
        bar.setFixedHeight(46)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        # Left Cluster
        self.logo_icon = ApertureLogoWidget(bar)
        self.brand_label = QLabel("LEICA // C270 OPTIX STUDIO")
        self.brand_label.setObjectName("BrandTitle")

        div1 = QFrame(bar)
        div1.setFixedSize(1, 22)
        div1.setStyleSheet("background-color: #262630; border: none;")

        self.camera_combo = QComboBox(bar)
        self.camera_combo.setFixedSize(170, 28)

        self.refresh_btn = RefreshIconButton(bar)

        self.backend_combo = QComboBox(bar)
        self.backend_combo.setFixedSize(105, 28)
        self.backend_combo.addItems(["DirectShow", "MSMF"])

        self.drv_cfg_btn = QPushButton("DRV CFG", bar)
        self.drv_cfg_btn.setFixedSize(68, 28)
        self.drv_cfg_btn.setToolTip("Open Native Windows DirectShow UVC Driver Property Sheet")

        layout.addWidget(self.logo_icon)
        layout.addWidget(self.brand_label)
        layout.addWidget(div1)
        layout.addWidget(self.camera_combo)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.backend_combo)
        layout.addWidget(self.drv_cfg_btn)

        layout.addStretch(1)

        # Center Telemetry Cluster
        self.badge_res = QLabel("RES: 1280x720")
        self.badge_res.setObjectName("TelemetryBadge")

        self.badge_fps = QLabel("FPS: 30.0")
        self.badge_fps.setObjectName("TelemetryBadge")

        self.badge_exp = QLabel("EXP: -5 (LOCKED)")
        self.badge_exp.setObjectName("TelemetryBadge")

        self.badge_gain = QLabel("GAIN: 110")
        self.badge_gain.setObjectName("TelemetryBadge")

        self.badge_wb = QLabel("WB: AUTO")
        self.badge_wb.setObjectName("TelemetryBadge")

        self.badge_lut = QLabel("LUT: PORTRA 400")
        self.badge_lut.setObjectName("TelemetryBadge")

        for b in (
            self.badge_res,
            self.badge_fps,
            self.badge_exp,
            self.badge_gain,
            self.badge_wb,
            self.badge_lut,
        ):
            layout.addWidget(b)

        layout.addStretch(1)

        # Right Cluster
        self.tally_dot = TallyDotWidget(bar)
        self.timecode_label = QLabel("00:00:00:00")
        self.timecode_label.setObjectName("MasterTimecode")

        layout.addWidget(self.tally_dot)
        layout.addWidget(self.timecode_label)

        return bar

    def _build_zone_b_left_dock(self) -> QFrame:
        dock = QFrame(self)
        dock.setObjectName("LeftInspectorDock")
        dock.setFixedWidth(320)

        dock_layout = QVBoxLayout(dock)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(0)

        scroll = QScrollArea(dock)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background-color: #0E0E12;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(12)

        # Card 1: C270 30-FPS HARDWARE ENGINE
        card1 = InspectorCard("C270 30-FPS HARDWARE ENGINE")
        self.sw_30fps_lock = ToggleSwitch("30 FPS Low-Light Lock (Manual Exp)", checked=True)
        self.sw_50hz_flicker = ToggleSwitch("50Hz Powerline Anti-Flicker", checked=True)
        self.sl_hw_exp = PrecisionSlider("Hardware Exposure", -11, -2, -5, step=1, decimals=0, suffix=" EV")
        self.sl_hw_gain = PrecisionSlider("Sensor Gain (ISO)", 0, 255, 110, step=1, decimals=0, suffix=" ISO")
        self.sl_backlight = PrecisionSlider("Backlight Comp", 0, 2, 0, step=1, decimals=0)

        card1.add_widget(self.sw_30fps_lock)
        card1.add_widget(self.sw_50hz_flicker)
        card1.add_widget(self.sl_hw_exp)
        card1.add_widget(self.sl_hw_gain)
        card1.add_widget(self.sl_backlight)
        vbox.addWidget(card1)

        # Card 2: SENSOR COLOR & WHITE BALANCE
        card2 = InspectorCard("SENSOR COLOR & WHITE BALANCE")
        self.sw_auto_wb = ToggleSwitch("Auto White Balance", checked=True)
        self.sl_wb_kelvin = PrecisionSlider("Color Temp (Kelvin)", 2800, 7500, 5000, step=100, decimals=0, suffix="K")
        self.sl_hw_bright = PrecisionSlider("Hardware Brightness", 0, 255, 128, step=1, decimals=0)
        self.sl_hw_contrast = PrecisionSlider("Hardware Contrast", 0, 255, 135, step=1, decimals=0)
        self.sl_hw_sat = PrecisionSlider("Hardware Saturation", 0, 255, 132, step=1, decimals=0)
        self.sl_hw_sharp = PrecisionSlider("Hardware Sharpness", 0, 255, 140, step=1, decimals=0)

        card2.add_widget(self.sw_auto_wb)
        card2.add_widget(self.sl_wb_kelvin)
        card2.add_widget(self.sl_hw_bright)
        card2.add_widget(self.sl_hw_contrast)
        card2.add_widget(self.sl_hw_sat)
        card2.add_widget(self.sl_hw_sharp)
        vbox.addWidget(card2)

        # Card 3: OPTICAL ISP & SUPER-RESOLUTION
        card3 = InspectorCard("OPTICAL ISP & SUPER-RESOLUTION")
        self.seg_resolution = SegmentedBar(["720p Native", "1080p Lanczos4 Master"], height=30)
        self.sl_clarity = PrecisionSlider("Optical Clarity (Unsharp Mask)", 0.0, 3.0, 0.80, step=0.05, decimals=2)
        self.sl_denoise = PrecisionSlider("Chroma/Luma Denoise", 0.0, 1.0, 0.15, step=0.05, decimals=2)
        self.sl_edge_detail = PrecisionSlider("Edge Detail Preservation", 0.1, 2.0, 1.00, step=0.05, decimals=2)

        card3.add_widget(self.seg_resolution)
        card3.add_widget(self.sl_clarity)
        card3.add_widget(self.sl_denoise)
        card3.add_widget(self.sl_edge_detail)
        vbox.addWidget(card3)

        # Card 4: FLUID PTZ & GEOMETRY
        card4 = InspectorCard("FLUID PTZ & GEOMETRY")
        self.sl_zoom = PrecisionSlider("Digital Optical Zoom", 1.00, 3.00, 1.00, step=0.02, decimals=2, suffix="x")
        self.sl_pan_x = PrecisionSlider("Pan X (Horizontal)", -1.00, 1.00, 0.00, step=0.02, decimals=2, bipolar=True)
        self.sl_tilt_y = PrecisionSlider("Tilt Y (Vertical)", -1.00, 1.00, 0.00, step=0.02, decimals=2, bipolar=True)

        geom_row = QHBoxLayout()
        geom_row.setSpacing(5)
        self.btn_mirror_h = QPushButton("Mirror H")
        self.btn_mirror_h.setCheckable(True)
        self.btn_mirror_h.setChecked(True)
        self.btn_mirror_h.setFixedHeight(30)

        self.btn_flip_v = QPushButton("Flip V")
        self.btn_flip_v.setCheckable(True)
        self.btn_flip_v.setFixedHeight(30)

        self.btn_rotate_90 = QPushButton("Rotate 90°")
        self.btn_rotate_90.setFixedHeight(30)

        self.btn_reset_ptz = QPushButton("Reset PTZ")
        self.btn_reset_ptz.setFixedHeight(30)

        for b in (self.btn_mirror_h, self.btn_flip_v, self.btn_rotate_90, self.btn_reset_ptz):
            geom_row.addWidget(b)

        card4.add_widget(self.sl_zoom)
        card4.add_widget(self.sl_pan_x)
        card4.add_widget(self.sl_tilt_y)
        card4.add_layout(geom_row)
        vbox.addWidget(card4)

        vbox.addStretch(1)
        scroll.setWidget(content)
        dock_layout.addWidget(scroll)
        return dock

    def _build_zone_d_right_dock(self) -> QFrame:
        dock = QFrame(self)
        dock.setObjectName("RightInspectorDock")
        dock.setFixedWidth(340)

        dock_layout = QVBoxLayout(dock)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(0)

        # Top 3-Tab Segmented Bar (Height: 36px)
        tab_container = QWidget(dock)
        tab_container.setStyleSheet("background-color: #0A0A0D; border-bottom: 1px solid #22222B;")
        tab_layout = QVBoxLayout(tab_container)
        tab_layout.setContentsMargins(8, 4, 8, 4)
        self.right_tabs = SegmentedBar(["COLOR & LUT", "AI STUDIO", "OVERLAYS"], height=30)
        tab_layout.addWidget(self.right_tabs)
        dock_layout.addWidget(tab_container)

        self.right_stack = QStackedWidget(dock)
        self.right_stack.addWidget(self._build_tab_color_lut())
        self.right_stack.addWidget(self._build_tab_ai_studio())
        self.right_stack.addWidget(self._build_tab_overlays())

        dock_layout.addWidget(self.right_stack, 1)
        return dock

    def _build_tab_color_lut(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background-color: #0E0E12;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(12)

        # Card 1: FILM LOOKS & 3D LUT ENGINE
        c1 = InspectorCard("FILM LOOKS & 3D LUT ENGINE")
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, look_name in enumerate(FILM_LOOK_NAMES):
            btn = FilmLookButton(look_name)
            if look_name == "Kodak Portra 400":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, n=look_name: self._on_film_look_selected(n))
            self._film_look_buttons[look_name] = btn
            grid.addWidget(btn, i // 2, i % 2)
        c1.add_layout(grid)

        cube_row = QHBoxLayout()
        cube_row.setSpacing(6)
        self.btn_load_cube = QPushButton("Load Custom .CUBE LUT...")
        self.btn_load_cube.setFixedHeight(28)
        self.btn_clear_cube = QPushButton("Clear LUT")
        self.btn_clear_cube.setFixedSize(78, 28)
        cube_row.addWidget(self.btn_load_cube, 1)
        cube_row.addWidget(self.btn_clear_cube)
        c1.add_layout(cube_row)

        self.sl_lut_mix = PrecisionSlider("LUT Intensity / Mix", 0, 100, 100, step=1, decimals=0, suffix="%")
        c1.add_widget(self.sl_lut_mix)
        vbox.addWidget(c1)

        # Card 2: PRIMARY COLOR WHEELS / GRADING
        c2 = InspectorCard("PRIMARY COLOR WHEELS / GRADING")
        self.sl_temp_shift = PrecisionSlider("Color Temp Shift", -100, 100, 0, step=1, decimals=0, bipolar=True)
        self.sl_tint_shift = PrecisionSlider("Tint (Green / Magenta)", -100, 100, 0, step=1, decimals=0, bipolar=True)
        self.sl_shadows = PrecisionSlider("Shadows (Lift)", -50, 50, 0, step=1, decimals=0, bipolar=True)
        self.sl_midtones = PrecisionSlider("Midtones (Gamma)", 0.50, 2.00, 1.00, step=0.02, decimals=2)
        self.sl_highlights = PrecisionSlider("Highlights (Gain)", -50, 50, 0, step=1, decimals=0, bipolar=True)
        self.sl_scurve = PrecisionSlider("S-Curve Contrast", 0.00, 1.00, 0.15, step=0.02, decimals=2)
        self.sl_vibrance = PrecisionSlider("Vibrance (Smart Sat)", -100, 100, 15, step=1, decimals=0, bipolar=True)

        for sl in (
            self.sl_temp_shift,
            self.sl_tint_shift,
            self.sl_shadows,
            self.sl_midtones,
            self.sl_highlights,
            self.sl_scurve,
            self.sl_vibrance,
        ):
            c2.add_widget(sl)
        vbox.addWidget(c2)

        # Card 3: OPTICAL TEXTURE & LENS
        c3 = InspectorCard("OPTICAL TEXTURE & LENS")
        self.sl_vignette = PrecisionSlider("Optical Vignette", 0.00, 1.00, 0.15, step=0.02, decimals=2)
        self.sl_grain = PrecisionSlider("Organic Film Grain", 0.00, 1.00, 0.00, step=0.02, decimals=2)
        self.btn_reset_color = QPushButton("Reset Color Grade")
        self.btn_reset_color.setFixedHeight(30)

        c3.add_widget(self.sl_vignette)
        c3.add_widget(self.sl_grain)
        c3.add_widget(self.btn_reset_color)
        vbox.addWidget(c3)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_tab_ai_studio(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background-color: #0E0E12;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(12)

        # Card 1: BACKGROUND & STUDIO LIGHTING MODE
        c1 = InspectorCard("BACKGROUND & STUDIO LIGHTING MODE")
        self.combo_ai_mode = QComboBox()
        self.combo_ai_mode.setFixedHeight(30)
        self.combo_ai_mode.addItems(
            [
                "Off (Natural Scene)",
                "Studio Spotlight (Dim Background)",
                "Optical Bokeh Blur (DSLR Portrait)",
                "Custom Studio Backdrop",
            ]
        )
        self.combo_ai_mode.setCurrentText("Studio Spotlight (Dim Background)")

        self.sl_spotlight_dim = PrecisionSlider("Spotlight Dimming %", 10, 85, 45, step=1, decimals=0, suffix="%")
        self.sl_bokeh_radius = PrecisionSlider("Bokeh Blur Radius", 5, 65, 25, step=2, decimals=0)
        self.sl_edge_feather = PrecisionSlider("Edge Feather / Spill Suppression", 1, 25, 7, step=1, decimals=0)

        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(6)
        swatches = [
            ("Obsidian", "#121216"),
            ("Slate", "#1E293B"),
            ("Plum", "#2E1035"),
            ("Forest", "#0F291E"),
        ]
        for label, hex_col in swatches:
            sbtn = QPushButton(label)
            sbtn.setFixedHeight(26)
            sbtn.setStyleSheet(
                f"background-color: {hex_col}; border: 1px solid #3E3E4E; color: #F4F4F6; font-size: 10px;"
            )
            sbtn.clicked.connect(lambda checked, h=hex_col: self._set_backdrop_color(h))
            swatch_row.addWidget(sbtn)

        backdrop_btn_row = QHBoxLayout()
        backdrop_btn_row.setSpacing(6)
        self.btn_pick_color = QPushButton("Pick Custom Color...")
        self.btn_pick_color.setFixedHeight(28)
        self.btn_load_backdrop = QPushButton("Load Backdrop Image...")
        self.btn_load_backdrop.setFixedHeight(28)
        backdrop_btn_row.addWidget(self.btn_pick_color)
        backdrop_btn_row.addWidget(self.btn_load_backdrop)

        c1.add_widget(self.combo_ai_mode)
        c1.add_widget(self.sl_spotlight_dim)
        c1.add_widget(self.sl_bokeh_radius)
        c1.add_widget(self.sl_edge_feather)
        c1.add_layout(swatch_row)
        c1.add_layout(backdrop_btn_row)
        vbox.addWidget(c1)

        # Card 2: AI CENTER STAGE (AUTO-FRAMING)
        c2 = InspectorCard("AI CENTER STAGE (AUTO-FRAMING)")
        self.sw_auto_framing = ToggleSwitch("AI Face Auto-Framing (Center Stage)", checked=False)
        self.sl_target_zoom = PrecisionSlider(
            "Subject Target Zoom", 1.15, 2.20, 1.35, step=0.05, decimals=2, suffix="x"
        )
        self.sl_gimbal_damping = PrecisionSlider("Gimbal Damping (Smoothness)", 0.02, 0.30, 0.08, step=0.01, decimals=2)

        c2.add_widget(self.sw_auto_framing)
        c2.add_widget(self.sl_target_zoom)
        c2.add_widget(self.sl_gimbal_damping)
        vbox.addWidget(c2)

        # Card 3: PORTRAIT SKIN RETOUCH
        c3 = InspectorCard("PORTRAIT SKIN RETOUCH")
        self.sl_skin_smooth = PrecisionSlider("Frequency Skin Smoothing", 0.00, 1.00, 0.00, step=0.05, decimals=2)
        c3.add_widget(self.sl_skin_smooth)
        vbox.addWidget(c3)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_tab_overlays(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background-color: #0E0E12;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(12)

        # Card 1: VIEWPORT TELEMETRY & GUIDES
        c1 = InspectorCard("VIEWPORT TELEMETRY & GUIDES")
        self.sw_show_hist = ToggleSwitch("Show Live Histogram", checked=True)
        self.sw_show_vu = ToggleSwitch("Show Audio VU Meter", checked=True)
        self.sw_guide_thirds = ToggleSwitch("Rule of Thirds Grid", checked=False)
        self.sw_guide_golden = ToggleSwitch("Golden Ratio Grid", checked=False)
        self.sw_guide_cross = ToggleSwitch("Center Crosshair & Safe Area", checked=False)
        self.sw_guide_anamorphic = ToggleSwitch("2.35:1 Anamorphic Crop Bars", checked=False)
        self.sw_guide_reel = ToggleSwitch("9:16 Vertical Reel Guide", checked=False)

        for sw in (
            self.sw_show_hist,
            self.sw_show_vu,
            self.sw_guide_thirds,
            self.sw_guide_golden,
            self.sw_guide_cross,
            self.sw_guide_anamorphic,
            self.sw_guide_reel,
        ):
            c1.add_widget(sw)
        vbox.addWidget(c1)

        # Card 2: LOWER THIRD BROADCAST GRAPHIC
        c2 = InspectorCard("LOWER THIRD BROADCAST GRAPHIC")
        self.sw_lower_third = ToggleSwitch("Show Lower Third Card", checked=False)
        self.ed_lt_name = QLineEdit("ALEXANDER VANCE")
        self.ed_lt_name.setPlaceholderText("Presenter Name")
        self.ed_lt_role = QLineEdit("DIRECTOR OF PHOTOGRAPHY // LIVE")
        self.ed_lt_role.setPlaceholderText("Title / Role")
        self.combo_lt_accent = QComboBox()
        self.combo_lt_accent.setFixedHeight(28)
        self.combo_lt_accent.addItems(
            [
                "Leica Amber (#E5A93C)",
                "Minimal Monochrome (#F4F4F6)",
                "Crimson Broadcast (#E11D48)",
            ]
        )

        c2.add_widget(self.sw_lower_third)
        c2.add_widget(self.ed_lt_name)
        c2.add_widget(self.ed_lt_role)
        c2.add_widget(self.combo_lt_accent)
        vbox.addWidget(c2)

        # Card 3: STUDIO WATERMARK & TIMECODE
        c3 = InspectorCard("STUDIO WATERMARK & TIMECODE")
        self.sw_watermark = ToggleSwitch("Show Custom PNG Logo", checked=False)
        wm_row = QHBoxLayout()
        wm_row.setSpacing(6)
        self.btn_select_wm = QPushButton("Select PNG Logo...")
        self.btn_select_wm.setFixedHeight(28)
        self.combo_wm_pos = QComboBox()
        self.combo_wm_pos.setFixedHeight(28)
        self.combo_wm_pos.addItems(["Top-Right", "Top-Left", "Bottom-Right", "Bottom-Left"])
        wm_row.addWidget(self.btn_select_wm, 1)
        wm_row.addWidget(self.combo_wm_pos)

        self.sl_wm_opacity = PrecisionSlider("Logo Opacity", 10, 100, 80, step=1, decimals=0, suffix="%")
        self.sw_burn_tc = ToggleSwitch("Burn-in Cinema Timecode & Date", checked=False)

        c3.add_widget(self.sw_watermark)
        c3.add_layout(wm_row)
        c3.add_widget(self.sl_wm_opacity)
        c3.add_widget(self.sw_burn_tc)
        vbox.addWidget(c3)

        vbox.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_zone_e_bottom_deck(self) -> QFrame:
        deck = QFrame(self)
        deck.setObjectName("BottomTransportDeck")
        deck.setFixedHeight(76)

        layout = QHBoxLayout(deck)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(10)

        # Left Cluster (Preset Management)
        lbl_preset = QLabel("PRESET:")
        lbl_preset.setObjectName("SectionHeaderLabel")

        self.combo_preset = QComboBox(deck)
        self.combo_preset.setFixedSize(200, 32)
        self._reload_preset_combo()

        self.btn_preset_save = QPushButton("Save", deck)
        self.btn_preset_save.setFixedSize(58, 32)

        self.btn_preset_del = QPushButton("Delete", deck)
        self.btn_preset_del.setFixedSize(58, 32)

        self.btn_reset_all = QPushButton("Reset All", deck)
        self.btn_reset_all.setFixedSize(74, 32)

        layout.addWidget(lbl_preset)
        layout.addWidget(self.combo_preset)
        layout.addWidget(self.btn_preset_save)
        layout.addWidget(self.btn_preset_del)
        layout.addWidget(self.btn_reset_all)

        layout.addStretch(1)

        # Center Cluster (Tactile Camera Transport Controls)
        self.combo_timer = QComboBox(deck)
        self.combo_timer.setFixedSize(85, 32)
        self.combo_timer.addItems(["Timer: Off", "3s Timer", "5s Timer", "10s Timer"])

        self.btn_flash = QPushButton("FLASH", deck)
        self.btn_flash.setCheckable(True)
        self.btn_flash.setFixedSize(68, 32)

        self.btn_shutter = ShutterButton(deck)
        self.btn_record = RecordButton(deck)
        self.btn_pause_rec = PauseRecordButton(deck)

        self.btn_burst = QPushButton("BURST 3X", deck)
        self.btn_burst.setFixedSize(78, 32)

        layout.addWidget(self.combo_timer)
        layout.addWidget(self.btn_flash)
        layout.addWidget(self.btn_shutter)
        layout.addWidget(self.btn_record)
        layout.addWidget(self.btn_pause_rec)
        layout.addWidget(self.btn_burst)

        layout.addStretch(1)

        # Right Cluster (Output & Routing)
        self.combo_snap_fmt = QComboBox(deck)
        self.combo_snap_fmt.setFixedSize(105, 32)
        self.combo_snap_fmt.addItems(["PNG Lossless", "JPG 100%"])

        self.btn_vcam = QPushButton("VIRTUAL CAM: OFF", deck)
        self.btn_vcam.setObjectName("VirtualCamButton")
        self.btn_vcam.setCheckable(True)
        self.btn_vcam.setFixedSize(150, 34)

        self.btn_gallery = QPushButton("OPEN GALLERY", deck)
        self.btn_gallery.setFixedSize(115, 34)

        layout.addWidget(self.combo_snap_fmt)
        layout.addWidget(self.btn_vcam)
        layout.addWidget(self.btn_gallery)

        return deck

    def _connect_signals(self) -> None:
        # Top Bar
        self.refresh_btn.clicked.connect(self._refresh_camera_devices)
        self.camera_combo.currentIndexChanged.connect(self._on_device_or_backend_changed)
        self.backend_combo.currentIndexChanged.connect(self._on_device_or_backend_changed)
        self.drv_cfg_btn.clicked.connect(self.camera_worker.request_driver_settings_dialog)

        # Left Dock Hardware & ISP
        self.sw_30fps_lock.toggled.connect(lambda v: self._set_param("manual_exposure_lock", v))
        self.sw_50hz_flicker.toggled.connect(lambda v: self._set_param("anti_flicker_50hz", v))
        self.sl_hw_exp.valueChanged.connect(lambda v: self._set_param("hardware_exposure", v))
        self.sl_hw_gain.valueChanged.connect(lambda v: self._set_param("hardware_gain", v))
        self.sl_backlight.valueChanged.connect(lambda v: self._set_param("backlight_comp", v))

        self.sw_auto_wb.toggled.connect(lambda v: self._set_param("auto_wb", v))
        self.sl_wb_kelvin.valueChanged.connect(lambda v: self._set_param("wb_kelvin", v))
        self.sl_hw_bright.valueChanged.connect(lambda v: self._set_param("hardware_brightness", v))
        self.sl_hw_contrast.valueChanged.connect(lambda v: self._set_param("hardware_contrast", v))
        self.sl_hw_sat.valueChanged.connect(lambda v: self._set_param("hardware_saturation", v))
        self.sl_hw_sharp.valueChanged.connect(lambda v: self._set_param("hardware_sharpness", v))

        self.seg_resolution.indexChanged.connect(lambda idx: self._set_param("upscale_1080p", idx == 1))
        self.sl_clarity.valueChanged.connect(lambda v: self._set_param("optical_clarity", v))
        self.sl_denoise.valueChanged.connect(lambda v: self._set_param("denoise_strength", v))
        self.sl_edge_detail.valueChanged.connect(lambda v: self._set_param("edge_detail_radius", v))

        self.sl_zoom.valueChanged.connect(self._on_ptz_slider_changed)
        self.sl_pan_x.valueChanged.connect(self._on_ptz_slider_changed)
        self.sl_tilt_y.valueChanged.connect(self._on_ptz_slider_changed)
        self.btn_mirror_h.toggled.connect(lambda v: self._set_param("mirror_h", v))
        self.btn_flip_v.toggled.connect(lambda v: self._set_param("flip_v", v))
        self.btn_rotate_90.clicked.connect(self._on_rotate_90_clicked)
        self.btn_reset_ptz.clicked.connect(self._on_reset_ptz)

        # Viewport interactive PTZ & Flash
        self.viewport.ptz_changed.connect(self._on_viewport_ptz_dragged)
        self.viewport.ptz_reset_requested.connect(self._on_reset_ptz)
        self.viewport.flash_peak_reached.connect(self._execute_immediate_snapshot)

        # Right Dock Tabs
        self.right_tabs.indexChanged.connect(self.right_stack.setCurrentIndex)

        # Tab 1: Color & LUT
        self.btn_load_cube.clicked.connect(self._on_load_cube_clicked)
        self.btn_clear_cube.clicked.connect(self._on_clear_cube_clicked)
        self.sl_lut_mix.valueChanged.connect(lambda v: self._set_param("lut_intensity", v))
        self.sl_temp_shift.valueChanged.connect(lambda v: self._set_param("temp_shift", v))
        self.sl_tint_shift.valueChanged.connect(lambda v: self._set_param("tint_shift", v))
        self.sl_shadows.valueChanged.connect(lambda v: self._set_param("shadows_lift", v))
        self.sl_midtones.valueChanged.connect(lambda v: self._set_param("midtones_gamma", v))
        self.sl_highlights.valueChanged.connect(lambda v: self._set_param("highlights_gain", v))
        self.sl_scurve.valueChanged.connect(lambda v: self._set_param("scurve_contrast", v))
        self.sl_vibrance.valueChanged.connect(lambda v: self._set_param("vibrance", v))
        self.sl_vignette.valueChanged.connect(lambda v: self._set_param("optical_vignette", v))
        self.sl_grain.valueChanged.connect(lambda v: self._set_param("film_grain", v))
        self.btn_reset_color.clicked.connect(self._on_reset_color_grade)

        # Tab 2: AI Studio
        self.combo_ai_mode.currentTextChanged.connect(lambda t: self._set_param("ai_mode", t))
        self.sl_spotlight_dim.valueChanged.connect(lambda v: self._set_param("spotlight_dim_pct", v))
        self.sl_bokeh_radius.valueChanged.connect(lambda v: self._set_param("bokeh_blur_radius", v))
        self.sl_edge_feather.valueChanged.connect(lambda v: self._set_param("edge_feather", v))
        self.btn_pick_color.clicked.connect(self._on_pick_backdrop_color)
        self.btn_load_backdrop.clicked.connect(self._on_load_backdrop_image)
        self.sw_auto_framing.toggled.connect(self._on_auto_framing_toggled)
        self.sl_target_zoom.valueChanged.connect(lambda v: self._set_param("subject_target_zoom", v))
        self.sl_gimbal_damping.valueChanged.connect(lambda v: self._set_param("gimbal_damping", v))
        self.sl_skin_smooth.valueChanged.connect(lambda v: self._set_param("skin_smoothing", v))

        # Tab 3: Overlays
        self.sw_show_hist.toggled.connect(self._on_hud_guide_toggled)
        self.sw_show_vu.toggled.connect(self._on_hud_guide_toggled)
        self.sw_guide_thirds.toggled.connect(self._on_hud_guide_toggled)
        self.sw_guide_golden.toggled.connect(self._on_hud_guide_toggled)
        self.sw_guide_cross.toggled.connect(self._on_hud_guide_toggled)
        self.sw_guide_anamorphic.toggled.connect(self._on_hud_guide_toggled)
        self.sw_guide_reel.toggled.connect(self._on_hud_guide_toggled)

        self.sw_lower_third.toggled.connect(lambda v: self._set_param("show_lower_third", v))
        self.ed_lt_name.textChanged.connect(lambda t: self._set_param("lower_third_name", t))
        self.ed_lt_role.textChanged.connect(lambda t: self._set_param("lower_third_role", t))
        self.combo_lt_accent.currentTextChanged.connect(lambda t: self._set_param("lower_third_accent", t))

        self.sw_watermark.toggled.connect(lambda v: self._set_param("show_watermark", v))
        self.btn_select_wm.clicked.connect(self._on_select_watermark_png)
        self.combo_wm_pos.currentTextChanged.connect(lambda t: self._set_param("watermark_position", t))
        self.sl_wm_opacity.valueChanged.connect(lambda v: self._set_param("watermark_opacity", v))
        self.sw_burn_tc.toggled.connect(lambda v: self._set_param("burn_in_timecode", v))

        # Zone E: Bottom Deck
        self.combo_preset.currentTextChanged.connect(self._on_preset_selected)
        self.btn_preset_save.clicked.connect(self._on_save_preset_clicked)
        self.btn_preset_del.clicked.connect(self._on_delete_preset_clicked)
        self.btn_reset_all.clicked.connect(self._on_reset_all_clicked)

        self.btn_shutter.clicked.connect(self._on_shutter_clicked)
        self.btn_burst.clicked.connect(self._on_burst_clicked)
        self.btn_record.clicked.connect(self._on_record_clicked)
        self.btn_pause_rec.clicked.connect(self._on_pause_record_clicked)
        self.btn_vcam.toggled.connect(self._on_virtual_cam_toggled)
        self.btn_gallery.clicked.connect(self._on_open_gallery)

        # Engine callbacks
        self.camera_worker.frame_ready.connect(self._on_frame_ready)
        self.audio_monitor.levels_updated.connect(self.viewport.set_audio_levels)
        self.recorder.recording_state_changed.connect(self._on_recording_state_changed)
        self.recorder.timecode_updated.connect(self.timecode_label.setText)
        self.virtual_cam.status_changed.connect(self._on_virtual_cam_status)

    # --- Device & Parameter Sync ---
    def _refresh_camera_devices(self) -> None:
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        devices = CameraWorker.enumerate_cameras()
        for idx, name in devices:
            self.camera_combo.addItem(name, idx)
        self.camera_combo.blockSignals(False)
        self._on_device_or_backend_changed()

    def _on_device_or_backend_changed(self) -> None:
        dev_idx = self.camera_combo.currentData()
        if dev_idx is None:
            dev_idx = 0
        backend = self.backend_combo.currentText()
        self.camera_worker.set_device(int(dev_idx), backend)

    def _set_param(self, key: str, value: Any) -> None:
        if self._updating_ui:
            return
        self.camera_worker.update_param(key, value)
        self._update_top_telemetry_badges()

    def _update_top_telemetry_badges(self) -> None:
        params = self.camera_worker.get_params_copy()
        if params.get("manual_exposure_lock", True):
            ev = int(round(float(params.get("hardware_exposure", -5.0))))
            self.badge_exp.setText(f"EXP: {ev} (LOCKED)")
        else:
            self.badge_exp.setText("EXP: AUTO")

        gain = int(round(float(params.get("hardware_gain", 110.0))))
        self.badge_gain.setText(f"GAIN: {gain}")

        if params.get("auto_wb", True):
            self.badge_wb.setText("WB: AUTO")
        else:
            k = int(round(float(params.get("wb_kelvin", 5000.0))))
            self.badge_wb.setText(f"WB: {k}K")

        look = str(params.get("film_look", "Kodak Portra 400")).upper()
        short_look = look.replace("KODAK ", "").replace("LEICA ", "")
        self.badge_lut.setText(f"LUT: {short_look}")

    def _on_frame_ready(self, frame_bgr, telemetry: Dict[str, Any]) -> None:
        self.viewport.update_frame(frame_bgr, telemetry)

        # Update Resolution & Dynamic FPS Badges
        w = telemetry.get("width", 1280)
        h = telemetry.get("height", 720)
        hq = " (HQ)" if telemetry.get("upscaled", False) else ""
        self.badge_res.setText(f"RES: {w}x{h}{hq}")

        fps = float(telemetry.get("fps", 30.0))
        self.badge_fps.setText(f"FPS: {fps:4.1f}")
        if fps >= 27.5:
            fps_col = "#10B981"
        elif fps >= 18.0:
            fps_col = "#F59E0B"
        else:
            fps_col = "#E11D48"
        self.badge_fps.setStyleSheet(
            f"background-color: #14141A; border: 1px solid #262632; border-radius: 4px; "
            f'padding: 3px 8px; color: {fps_col}; font-family: "Consolas", monospace; '
            f"font-size: 11px; font-weight: 700;"
        )

    # --- PTZ & Geometry ---
    def _on_ptz_slider_changed(self) -> None:
        if self._updating_ui:
            return
        z = self.sl_zoom.value()
        px = self.sl_pan_x.value()
        py = self.sl_tilt_y.value()
        self.viewport.set_ptz_targets(z, px, py)
        self.camera_worker.update_param("digital_zoom", z)
        self.camera_worker.update_param("pan_x", px)
        self.camera_worker.update_param("tilt_y", py)

    def _on_viewport_ptz_dragged(self, z: float, px: float, py: float) -> None:
        self._updating_ui = True
        self.sl_zoom.setValue(z)
        self.sl_pan_x.setValue(px)
        self.sl_tilt_y.setValue(py)
        self._updating_ui = False
        self.camera_worker.update_param("digital_zoom", z)
        self.camera_worker.update_param("pan_x", px)
        self.camera_worker.update_param("tilt_y", py)

    def _on_rotate_90_clicked(self) -> None:
        params = self.camera_worker.get_params_copy()
        nxt = (int(params.get("rotate_quadrant", 0)) + 1) % 4
        self.camera_worker.update_param("rotate_quadrant", nxt)

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

    # --- Color & LUT ---
    def _on_film_look_selected(self, look_name: str) -> None:
        for name, btn in self._film_look_buttons.items():
            btn.setChecked(name == look_name)
        self._set_param("film_look", look_name)

    def _on_load_cube_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select 3D/1D .CUBE LUT File",
            str(Path.home()),
            "Cube LUT Files (*.cube *.CUBE);;All Files (*)",
        )
        if file_path:
            self._set_param("custom_cube_path", file_path)
            self.badge_lut.setText(f"LUT: {Path(file_path).stem.upper()[:12]}")

    def _on_clear_cube_clicked(self) -> None:
        self._set_param("custom_cube_path", "")
        self._update_top_telemetry_badges()

    def _on_reset_color_grade(self) -> None:
        self._updating_ui = True
        self.sl_lut_mix.setValue(100)
        self.sl_temp_shift.setValue(0)
        self.sl_tint_shift.setValue(0)
        self.sl_shadows.setValue(0)
        self.sl_midtones.setValue(1.00)
        self.sl_highlights.setValue(0)
        self.sl_scurve.setValue(0.15)
        self.sl_vibrance.setValue(15)
        self.sl_vignette.setValue(0.15)
        self.sl_grain.setValue(0.00)
        self._updating_ui = False
        for k in (
            "lut_intensity",
            "temp_shift",
            "tint_shift",
            "shadows_lift",
            "midtones_gamma",
            "highlights_gain",
            "scurve_contrast",
            "vibrance",
            "optical_vignette",
            "film_grain",
        ):
            self.camera_worker.update_param(k, DEFAULT_STUDIO_PARAMS[k])

    # --- AI Studio ---
    def _set_backdrop_color(self, hex_col: str) -> None:
        self.camera_worker.update_param("backdrop_image_path", "")
        self.camera_worker.update_param("backdrop_color_hex", hex_col)
        self.combo_ai_mode.setCurrentText("Custom Studio Backdrop")

    def _on_pick_backdrop_color(self) -> None:
        col = QColorDialog.getColor(QColor("#121216"), self, "Select Studio Backdrop Color")
        if col.isValid():
            self._set_backdrop_color(col.name())

    def _on_load_backdrop_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Studio Backdrop Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if file_path:
            self.camera_worker.update_param("backdrop_image_path", file_path)
            self.combo_ai_mode.setCurrentText("Custom Studio Backdrop")

    def _on_auto_framing_toggled(self, checked: bool) -> None:
        self.viewport._auto_framing_active = bool(checked)
        self._set_param("auto_framing", checked)

    # --- Overlays ---
    def _on_hud_guide_toggled(self) -> None:
        self.viewport.show_histogram = self.sw_show_hist.isChecked()
        self.viewport.show_vu_meter = self.sw_show_vu.isChecked()
        self.viewport.guide_thirds = self.sw_guide_thirds.isChecked()
        self.viewport.guide_golden = self.sw_guide_golden.isChecked()
        self.viewport.guide_crosshair_safe = self.sw_guide_cross.isChecked()
        self.viewport.guide_anamorphic = self.sw_guide_anamorphic.isChecked()
        self.viewport.guide_vertical_reel = self.sw_guide_reel.isChecked()
        self.viewport.update()

    def _on_select_watermark_png(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Broadcast Watermark PNG",
            str(Path.home()),
            "PNG Images (*.png)",
        )
        if file_path:
            self.camera_worker.update_param("watermark_path", file_path)
            self.sw_watermark.setChecked(True)

    # --- Presets ---
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
            self.sw_30fps_lock.setChecked(bool(params.get("manual_exposure_lock", True)))
            self.sw_50hz_flicker.setChecked(bool(params.get("anti_flicker_50hz", True)))
            self.sl_hw_exp.setValue(float(params.get("hardware_exposure", -5.0)))
            self.sl_hw_gain.setValue(float(params.get("hardware_gain", 110.0)))
            self.sl_backlight.setValue(float(params.get("backlight_comp", 0.0)))

            self.sw_auto_wb.setChecked(bool(params.get("auto_wb", True)))
            self.sl_wb_kelvin.setValue(float(params.get("wb_kelvin", 5000.0)))
            self.sl_hw_bright.setValue(float(params.get("hardware_brightness", 128.0)))
            self.sl_hw_contrast.setValue(float(params.get("hardware_contrast", 135.0)))
            self.sl_hw_sat.setValue(float(params.get("hardware_saturation", 132.0)))
            self.sl_hw_sharp.setValue(float(params.get("hardware_sharpness", 140.0)))

            self.seg_resolution.set_current_index(1 if params.get("upscale_1080p", False) else 0)
            self.sl_clarity.setValue(float(params.get("optical_clarity", 0.80)))
            self.sl_denoise.setValue(float(params.get("denoise_strength", 0.15)))
            self.sl_edge_detail.setValue(float(params.get("edge_detail_radius", 1.00)))

            self.sl_zoom.setValue(float(params.get("digital_zoom", 1.00)))
            self.sl_pan_x.setValue(float(params.get("pan_x", 0.00)))
            self.sl_tilt_y.setValue(float(params.get("tilt_y", 0.00)))
            self.btn_mirror_h.setChecked(bool(params.get("mirror_h", True)))
            self.btn_flip_v.setChecked(bool(params.get("flip_v", False)))

            look = str(params.get("film_look", "Kodak Portra 400"))
            for name, btn in self._film_look_buttons.items():
                btn.setChecked(name == look)

            self.sl_lut_mix.setValue(float(params.get("lut_intensity", 100.0)))
            self.sl_temp_shift.setValue(float(params.get("temp_shift", 0.0)))
            self.sl_tint_shift.setValue(float(params.get("tint_shift", 0.0)))
            self.sl_shadows.setValue(float(params.get("shadows_lift", 0.0)))
            self.sl_midtones.setValue(float(params.get("midtones_gamma", 1.00)))
            self.sl_highlights.setValue(float(params.get("highlights_gain", 0.0)))
            self.sl_scurve.setValue(float(params.get("scurve_contrast", 0.15)))
            self.sl_vibrance.setValue(float(params.get("vibrance", 15.0)))
            self.sl_vignette.setValue(float(params.get("optical_vignette", 0.15)))
            self.sl_grain.setValue(float(params.get("film_grain", 0.00)))

            self.combo_ai_mode.setCurrentText(str(params.get("ai_mode", "Studio Spotlight (Dim Background)")))
            self.sl_spotlight_dim.setValue(float(params.get("spotlight_dim_pct", 45.0)))
            self.sl_bokeh_radius.setValue(float(params.get("bokeh_blur_radius", 25.0)))
            self.sl_edge_feather.setValue(float(params.get("edge_feather", 7.0)))
            self.sw_auto_framing.setChecked(bool(params.get("auto_framing", False)))
            self.sl_target_zoom.setValue(float(params.get("subject_target_zoom", 1.35)))
            self.sl_gimbal_damping.setValue(float(params.get("gimbal_damping", 0.08)))
            self.sl_skin_smooth.setValue(float(params.get("skin_smoothing", 0.00)))

            self.sw_lower_third.setChecked(bool(params.get("show_lower_third", False)))
            self.ed_lt_name.setText(str(params.get("lower_third_name", "ALEXANDER VANCE")))
            self.ed_lt_role.setText(str(params.get("lower_third_role", "DIRECTOR OF PHOTOGRAPHY // LIVE")))
        finally:
            self._updating_ui = False

        self.camera_worker.update_all_params(params)
        self._update_top_telemetry_badges()

    def _on_preset_selected(self, preset_name: str) -> None:
        if not preset_name:
            return
        params = self.preset_manager.get_preset(preset_name)
        self._apply_params_to_ui(params)

    def _on_save_preset_clicked(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "Save Custom Studio Preset",
            "Enter Preset Name:",
            text="Custom C270 Look",
        )
        if ok and name.strip():
            current = self.camera_worker.get_params_copy()
            self.preset_manager.save_user_preset(name.strip(), current)
            self._reload_preset_combo(select_name=name.strip())

    def _on_delete_preset_clicked(self) -> None:
        cur = self.combo_preset.currentText()
        if self.preset_manager.delete_user_preset(cur):
            self._reload_preset_combo()
        else:
            QMessageBox.information(
                self,
                "Factory Preset Protected",
                "Built-in Leica C270 factory calibration presets cannot be deleted.",
            )

    def _on_reset_all_clicked(self) -> None:
        self._apply_params_to_ui(DEFAULT_STUDIO_PARAMS)

    # --- Transport: Shutter, Timer, Flash, Burst, Record, Virtual Cam ---
    def _on_shutter_clicked(self) -> None:
        timer_txt = self.combo_timer.currentText()
        if "3s" in timer_txt:
            self._start_countdown(3)
        elif "5s" in timer_txt:
            self._start_countdown(5)
        elif "10s" in timer_txt:
            self._start_countdown(10)
        else:
            self._trigger_flash_or_snapshot()

    def _start_countdown(self, seconds: int) -> None:
        self._countdown_remaining = seconds
        self.viewport.set_countdown(self._countdown_remaining)
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
        fmt = self.combo_snap_fmt.currentText()
        self.camera_worker.trigger_snapshot(fmt=fmt, count=1, interval_sec=0.0)

    def _on_burst_clicked(self) -> None:
        fmt = self.combo_snap_fmt.currentText()
        self.camera_worker.trigger_snapshot(fmt=fmt, count=3, interval_sec=0.18)

    def _on_record_clicked(self) -> None:
        if not self.recorder.is_recording:
            params = self.camera_worker.get_params_copy()
            upscale = bool(params.get("upscale_1080p", False))
            w, h = (1920, 1080) if upscale else (1280, 720)
            self.recorder.start_recording(width=w, height=h, fps=30.0)
        else:
            self.recorder.stop_recording()

    def _on_pause_record_clicked(self) -> None:
        if self.recorder.is_recording:
            paused = self.recorder.toggle_pause()
            self.btn_pause_rec.setChecked(paused)

    def _on_recording_state_changed(self, is_recording: bool, is_paused: bool) -> None:
        self.btn_record.setChecked(is_recording)
        self.btn_pause_rec.setEnabled(is_recording)
        self.btn_pause_rec.setChecked(is_paused)
        self.tally_dot.set_recording(is_recording and not is_paused)
        self.viewport.set_tally_state(is_recording, self.virtual_cam.is_active)

    def _on_virtual_cam_toggled(self, checked: bool) -> None:
        params = self.camera_worker.get_params_copy()
        upscale = bool(params.get("upscale_1080p", False))
        w, h = (1920, 1080) if upscale else (1280, 720)
        ok = self.virtual_cam.set_enabled(checked, width=w, height=h)
        if checked and not ok:
            self.btn_vcam.blockSignals(True)
            self.btn_vcam.setChecked(False)
            self.btn_vcam.setText("VIRTUAL CAM: OFF")
            self.btn_vcam.blockSignals(False)

    def _on_virtual_cam_status(self, active: bool, msg: str) -> None:
        self.btn_vcam.setText("VIRTUAL CAM: LIVE" if active else "VIRTUAL CAM: OFF")
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
