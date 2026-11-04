# -*- coding: utf-8 -*-
"""
Center Cinema Viewport & Interactive On-Screen Display (OSD) HUD (`ui/viewport_hud.py`).
Implements:
- Aspect-ratio-preserving video canvas with 2px Dynamic Tally Frame (#262630 idle,
  #E11D48 recording, #10B981 virtual cam)
- Interactive Mouse PTZ: Scroll wheel zoom (±0.08x/notch), Left-click drag Pan/Tilt,
  Double-click reset PTZ to (1.0x, 0.0, 0.0)
- Top-Left Floating 64-Bin RGB + Luminance Histogram (`x: 18, y: 18, w: 190, h: 95`)
- Top-Right PTZ Radar Box (`w: 120, h: 68`) when zoom > 1.01x or Auto-Framing is active
- Bottom-Left Audio Peak VU Meter (`x: 18, bottom: 18, w: 230, h: 32`)
- Composition Guide Overlays (Rule of Thirds, Golden Ratio Phi, Center Crosshair + Safe
  Action/Title boxes, 2.35:1 Anamorphic Letterbox, 9:16 Vertical Social Reel Guide)
- Softbox Screen Flash Overlay (#FFFDF8 for 280ms + fade out)
- Countdown Timer Overlay (72px Consolas bold inside 120x120px #B30A0A0D circle with #E5A93C ring)
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainterPath,
    QMouseEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import QWidget


class ViewportCanvas(QWidget):
    """Custom QPainter cinema viewport and interactive PTZ + HUD overlay surface."""

    ptz_changed = pyqtSignal(float, float, float)  # (zoom, pan_x, tilt_y)
    ptz_reset_requested = pyqtSignal()
    flash_peak_reached = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(540, 360)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #070709;")

        self._qimage: Optional[QImage] = None
        self._histogram: Dict[str, np.ndarray] = {}
        self._ptz_state: Tuple[float, float, float] = (1.0, 0.0, 0.0)
        self._auto_framing_active: bool = False

        # Tally states
        self._is_recording: bool = False
        self._is_virtual_cam: bool = False

        # Audio VU state
        self._rms_db: float = -60.0
        self._peak_db: float = -60.0
        self._mic_available: bool = False

        # Overlay toggles
        self.show_histogram: bool = True
        self.show_vu_meter: bool = True
        self.guide_thirds: bool = False
        self.guide_golden: bool = False
        self.guide_crosshair_safe: bool = False
        self.guide_anamorphic: bool = False
        self.guide_vertical_reel: bool = False

        # Interactive mouse drag state
        self._dragging: bool = False
        self._last_mouse_pos: QPointF = QPointF(0.0, 0.0)
        self._target_zoom: float = 1.00
        self._target_pan_x: float = 0.00
        self._target_pan_y: float = 0.00

        # Countdown overlay state
        self._countdown_value: int = 0

        # Softbox flash overlay state
        self._flash_alpha: float = 0.0
        self._flash_hold_ticks: int = 0
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(20)
        self._flash_timer.timeout.connect(self._on_flash_tick)

    def set_ptz_targets(self, zoom: float, pan_x: float, tilt_y: float) -> None:
        self._target_zoom = float(zoom)
        self._target_pan_x = float(pan_x)
        self._target_pan_y = float(tilt_y)

    def set_tally_state(self, is_recording: bool, is_virtual_cam: bool) -> None:
        self._is_recording = bool(is_recording)
        self._is_virtual_cam = bool(is_virtual_cam)
        self.update()

    def set_audio_levels(self, rms_db: float, peak_db: float, mic_available: bool) -> None:
        self._rms_db = float(rms_db)
        self._peak_db = float(peak_db)
        self._mic_available = bool(mic_available)
        if self.show_vu_meter:
            self.update()

    def set_countdown(self, val: int) -> None:
        self._countdown_value = int(val)
        self.update()

    def trigger_softbox_flash(self) -> None:
        """
        Fills the entire viewport with warm studio white (#FFFDF8) for 280ms (14 ticks @ 20ms)
        before emitting flash_peak_reached, then fades out smoothly.
        """
        self._flash_alpha = 1.0
        self._flash_hold_ticks = 14
        self._flash_timer.start()
        self.update()

    def _on_flash_tick(self) -> None:
        if self._flash_hold_ticks > 0:
            self._flash_hold_ticks -= 1
            if self._flash_hold_ticks == 2:
                self.flash_peak_reached.emit()
            self.update()
            return

        self._flash_alpha -= 0.12
        if self._flash_alpha <= 0.0:
            self._flash_alpha = 0.0
            self._flash_timer.stop()
        self.update()

    def update_frame(self, frame_bgr: np.ndarray, telemetry: Dict[str, Any]) -> None:
        h, w, ch = frame_bgr.shape
        rgb = frame_bgr[:, :, ::-1].copy()
        bytes_per_line = ch * w
        self._qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        self._histogram = telemetry.get("histogram", {})
        self._ptz_state = telemetry.get("ptz", (1.0, 0.0, 0.0))
        self.update()

    # --- Interactive PTZ Mouse Handlers ---
    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta != 0:
            step = 0.08 if delta > 0 else -0.08
            self._target_zoom = max(1.00, min(3.00, round(self._target_zoom + step, 2)))
            if self._target_zoom <= 1.01:
                self._target_pan_x = 0.0
                self._target_pan_y = 0.0
            self.ptz_changed.emit(self._target_zoom, self._target_pan_x, self._target_pan_y)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._target_zoom > 1.01:
            self._dragging = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and self._target_zoom > 1.01:
            pos = event.position()
            dx = (pos.x() - self._last_mouse_pos.x()) / max(100.0, float(self.width()) * 0.35)
            dy = (pos.y() - self._last_mouse_pos.y()) / max(100.0, float(self.height()) * 0.35)
            self._last_mouse_pos = pos
            self._target_pan_x = max(-1.0, min(1.0, self._target_pan_x - dx))
            self._target_pan_y = max(-1.0, min(1.0, self._target_pan_y - dy))
            self.ptz_changed.emit(self._target_zoom, self._target_pan_x, self._target_pan_y)
            event.accept()
            return
        if self._target_zoom > 1.01:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(
                Qt.CursorShape.OpenHandCursor if self._target_zoom > 1.01 else Qt.CursorShape.ArrowCursor
            )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._target_zoom = 1.00
            self._target_pan_x = 0.00
            self._target_pan_y = 0.00
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.ptz_reset_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # --- QPainter Rendering Pipeline ---
    def _compute_video_rect(self) -> QRectF:
        pad = 14.0
        avail_w = max(64.0, float(self.width()) - pad * 2.0)
        avail_h = max(36.0, float(self.height()) - pad * 2.0)
        target_aspect = 16.0 / 9.0
        if avail_w / avail_h > target_aspect:
            vh = avail_h
            vw = vh * target_aspect
        else:
            vw = avail_w
            vh = vw / target_aspect
        vx = (float(self.width()) - vw) * 0.5
        vy = (float(self.height()) - vh) * 0.5
        return QRectF(vx, vy, vw, vh)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Void background #070709
        painter.fillRect(self.rect(), QColor("#070709"))

        vrect = self._compute_video_rect()

        if self._qimage is not None:
            painter.drawImage(vrect, self._qimage)
        else:
            painter.fillRect(vrect, QColor("#0E0E12"))

        # Composition Guide Overlays inside vrect
        self._draw_composition_guides(painter, vrect)

        # Dynamic 2px Tally Frame around active video rectangle
        if self._is_recording:
            tally_col = QColor("#E11D48")
        elif self._is_virtual_cam:
            tally_col = QColor("#10B981")
        else:
            tally_col = QColor("#262630")

        painter.setPen(QPen(tally_col, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(vrect)

        # Top-Left Floating 64-Bin RGB + Luminance Histogram (x: 18, y: 18, w: 190, h: 95)
        if self.show_histogram:
            self._draw_histogram_hud(painter, vrect)

        # Top-Right PTZ Radar Box (w: 120, h: 68) when zoom > 1.01x or Auto-Framing
        cur_zoom = self._ptz_state[0]
        if cur_zoom > 1.01 or self._auto_framing_active:
            self._draw_ptz_radar_hud(painter, vrect)

        # Bottom-Left Audio Peak VU Meter (x: 18, bottom: 18, w: 230, h: 32)
        if self.show_vu_meter:
            self._draw_audio_vu_hud(painter, vrect)

        # Countdown Timer Overlay
        if self._countdown_value > 0:
            self._draw_countdown_overlay(painter, vrect)

        # Softbox Screen Flash Overlay
        if self._flash_alpha > 0.005:
            flash_col = QColor(255, 253, 248, int(round(self._flash_alpha * 255)))
            painter.fillRect(self.rect(), flash_col)

        painter.end()

    def _draw_composition_guides(self, painter: QPainter, vrect: QRectF) -> None:
        painter.save()
        painter.setClipRect(vrect)

        vx, vy, vw, vh = vrect.x(), vrect.y(), vrect.width(), vrect.height()

        # 1. 2.35:1 Cinema Anamorphic Letterbox
        if self.guide_anamorphic:
            target_h = vw / 2.35
            if target_h < vh:
                bar_h = (vh - target_h) * 0.5
                matte = QColor(0, 0, 0, 217)  # #D9000000
                painter.fillRect(QRectF(vx, vy, vw, bar_h), matte)
                painter.fillRect(QRectF(vx, vy + vh - bar_h, vw, bar_h), matte)
                painter.setPen(QPen(QColor(229, 169, 60, 140), 1.0))
                painter.drawLine(QPointF(vx, vy + bar_h), QPointF(vx + vw, vy + bar_h))
                painter.drawLine(QPointF(vx, vy + vh - bar_h), QPointF(vx + vw, vy + vh - bar_h))

        # 2. 9:16 Vertical Social Reel Guide
        if self.guide_vertical_reel:
            reel_w = vh * (9.0 / 16.0)
            if reel_w < vw:
                wing_w = (vw - reel_w) * 0.5
                wing_dim = QColor(0, 0, 0, 166)  # 65% dim
                painter.fillRect(QRectF(vx, vy, wing_w, vh), wing_dim)
                painter.fillRect(QRectF(vx + vw - wing_w, vy, wing_w, vh), wing_dim)
                painter.setPen(QPen(QColor("#E5A93C"), 1.2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRectF(vx + wing_w, vy, reel_w, vh))

        # 3. Rule of Thirds (1/3 and 2/3)
        if self.guide_thirds:
            painter.setPen(QPen(QColor(255, 255, 255, 102), 1.0))
            for frac in (1.0 / 3.0, 2.0 / 3.0):
                painter.drawLine(QPointF(vx + vw * frac, vy), QPointF(vx + vw * frac, vy + vh))
                painter.drawLine(QPointF(vx, vy + vh * frac), QPointF(vx + vw, vy + vh * frac))

        # 4. Golden Ratio Phi Grid (0.382 and 0.618)
        if self.guide_golden:
            painter.setPen(QPen(QColor(229, 169, 60, 136), 1.0))
            for frac in (0.382, 0.618):
                painter.drawLine(QPointF(vx + vw * frac, vy), QPointF(vx + vw * frac, vy + vh))
                painter.drawLine(QPointF(vx, vy + vh * frac), QPointF(vx + vw, vy + vh * frac))

        # 5. Center Crosshair + Safe Action (90%) & Safe Title (80%)
        if self.guide_crosshair_safe:
            painter.setPen(QPen(QColor(255, 255, 255, 95), 1.0, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # 90% Safe Action
            act_rect = QRectF(vx + vw * 0.05, vy + vh * 0.05, vw * 0.90, vh * 0.90)
            painter.drawRect(act_rect)
            # 80% Safe Title
            tit_rect = QRectF(vx + vw * 0.10, vy + vh * 0.10, vw * 0.80, vh * 0.80)
            painter.drawRect(tit_rect)

            # Center Crosshair (24px gap-crossed hairlines)
            cx = vx + vw * 0.5
            cy = vy + vh * 0.5
            painter.setPen(QPen(QColor("#E5A93C"), 1.2))
            painter.drawLine(QPointF(cx - 24.0, cy), QPointF(cx - 5.0, cy))
            painter.drawLine(QPointF(cx + 5.0, cy), QPointF(cx + 24.0, cy))
            painter.drawLine(QPointF(cx, cy - 24.0), QPointF(cx, cy - 5.0))
            painter.drawLine(QPointF(cx, cy + 5.0), QPointF(cx, cy + 24.0))

        painter.restore()

    def _draw_histogram_hud(self, painter: QPainter, vrect: QRectF) -> None:
        painter.save()
        hx = vrect.x() + 18.0
        hy = vrect.y() + 18.0
        hw = 190.0
        hh = 95.0
        box = QRectF(hx, hy, hw, hh)

        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        painter.setBrush(QColor(10, 10, 14, 195))
        painter.drawRoundedRect(box, 6.0, 6.0)

        # Label
        painter.setPen(QColor("#9CA3AF"))
        f = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(
            QRectF(hx + 8.0, hy + 4.0, hw - 16.0, 14.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "RGB // LUMA HISTOGRAM",
        )

        plot_x = hx + 8.0
        plot_y = hy + 20.0
        plot_w = hw - 16.0
        plot_h = hh - 26.0

        # Subtle grid lines
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        for g_frac in (0.25, 0.5, 0.75):
            gx = plot_x + plot_w * g_frac
            painter.drawLine(QPointF(gx, plot_y), QPointF(gx, plot_y + plot_h))

        channels = [
            ("b", QColor("#0A84FF")),
            ("g", QColor("#32D74B")),
            ("r", QColor("#FF453A")),
            ("luma", QColor("#F4F4F6")),
        ]
        for key, col in channels:
            arr = self._histogram.get(key)
            if arr is None or len(arr) == 0:
                continue
            n = len(arr)
            path = QPainterPath()
            fill_path = QPainterPath()
            fill_path.moveTo(plot_x, plot_y + plot_h)

            for i in range(n):
                px = plot_x + (i / float(n - 1)) * plot_w
                py = plot_y + plot_h - float(arr[i]) * plot_h
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
                fill_path.lineTo(px, py)

            fill_path.lineTo(plot_x + plot_w, plot_y + plot_h)
            fill_path.closeSubpath()

            fill_col = QColor(col.red(), col.green(), col.blue(), 45)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_col)
            painter.drawPath(fill_path)

            painter.setPen(QPen(col, 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        painter.restore()

    def _draw_ptz_radar_hud(self, painter: QPainter, vrect: QRectF) -> None:
        painter.save()
        rw = 120.0
        rh = 68.0
        rx = vrect.right() - rw - 18.0
        ry = vrect.y() + 18.0
        outer = QRectF(rx, ry, rw, rh)

        painter.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
        painter.setBrush(QColor(10, 10, 14, 195))
        painter.drawRoundedRect(outer, 4.0, 4.0)

        zoom, pan_x, pan_y = self._ptz_state
        zoom = max(1.0, float(zoom))
        cw = rw / zoom
        ch = rh / zoom
        max_dx = (rw - cw) * 0.5
        max_dy = (rh - ch) * 0.5
        cx = rx + rw * 0.5 + np.clip(pan_x, -1.0, 1.0) * max_dx
        cy = ry + rh * 0.5 + np.clip(pan_y, -1.0, 1.0) * max_dy
        crop_rect = QRectF(cx - cw * 0.5, cy - ch * 0.5, cw, ch)

        painter.setPen(QPen(QColor("#E5A93C"), 1.5))
        painter.setBrush(QColor(229, 169, 60, 40))
        painter.drawRect(crop_rect)

        f = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(f)
        painter.setPen(QColor("#E5A93C"))
        painter.drawText(
            QRectF(rx + 5.0, ry + rh - 14.0, rw - 10.0, 12.0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"PTZ {zoom:.2f}x",
        )
        painter.restore()

    def _draw_audio_vu_hud(self, painter: QPainter, vrect: QRectF) -> None:
        painter.save()
        vw = 230.0
        vh = 32.0
        vx = vrect.x() + 18.0
        vy = vrect.bottom() - vh - 18.0
        box = QRectF(vx, vy, vw, vh)

        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        painter.setBrush(QColor(10, 10, 14, 195))
        painter.drawRoundedRect(box, 6.0, 6.0)

        f = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(f)
        painter.setPen(QColor("#9CA3AF"))
        painter.drawText(
            QRectF(vx + 8.0, vy, 46.0, vh),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "MIC VU",
        )

        bar_x = vx + 54.0
        bar_w = 122.0
        bar_y1 = vy + 10.0
        bar_y2 = vy + 18.0
        bar_h = 4.5

        # Background tracks
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#22222B"))
        painter.drawRoundedRect(QRectF(bar_x, bar_y1, bar_w, bar_h), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(bar_x, bar_y2, bar_w, bar_h), 1.5, 1.5)

        # Normalize dB [-60..0] -> [0..1]
        norm_rms = float(np.clip((self._rms_db + 60.0) / 60.0, 0.0, 1.0))
        norm_peak = float(np.clip((self._peak_db + 60.0) / 60.0, 0.0, 1.0))

        # Thresholds: -18dB is (42/60)=0.70, -6dB is (54/60)=0.90
        def _draw_segmented_bar(by: float, level: float) -> None:
            if level <= 0.005:
                return
            g_end = min(level, 0.70)
            painter.setBrush(QColor("#10B981"))
            painter.drawRect(QRectF(bar_x, by, bar_w * g_end, bar_h))

            if level > 0.70:
                a_end = min(level, 0.90)
                painter.setBrush(QColor("#E5A93C"))
                painter.drawRect(QRectF(bar_x + bar_w * 0.70, by, bar_w * (a_end - 0.70), bar_h))

            if level > 0.90:
                painter.setBrush(QColor("#E11D48"))
                painter.drawRect(QRectF(bar_x + bar_w * 0.90, by, bar_w * (level - 0.90), bar_h))

        _draw_segmented_bar(bar_y1, norm_rms)
        _draw_segmented_bar(bar_y2, max(0.0, norm_rms * 0.96))

        # Peak-hold white tick mark
        if norm_peak > 0.02:
            px = bar_x + bar_w * norm_peak
            painter.setPen(QPen(QColor("#F4F4F6"), 1.5))
            painter.drawLine(QPointF(px, bar_y1 - 1.0), QPointF(px, bar_y2 + bar_h + 1.0))

        # Numeric dB readout
        db_txt = f"{self._rms_db:4.0f}dB" if self._mic_available else "MUTE"
        painter.setPen(QColor("#E5A93C") if self._mic_available else QColor("#71717A"))
        painter.drawText(
            QRectF(bar_x + bar_w + 4.0, vy, 44.0, vh),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            db_txt,
        )
        painter.restore()

    def _draw_countdown_overlay(self, painter: QPainter, vrect: QRectF) -> None:
        painter.save()
        cx = vrect.center().x()
        cy = vrect.center().y()
        circle_rect = QRectF(cx - 60.0, cy - 60.0, 120.0, 120.0)

        painter.setPen(QPen(QColor("#E5A93C"), 3.0))
        painter.setBrush(QColor(10, 10, 13, 195))
        painter.drawEllipse(circle_rect)

        f = QFont("Consolas", 48, QFont.Weight.Bold)
        painter.setFont(f)
        painter.setPen(QColor("#F4F4F6"))
        painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, str(self._countdown_value))
        painter.restore()
