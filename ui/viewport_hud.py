# -*- coding: utf-8 -*-
"""
Spacious Hero Viewport Canvas (`ui/viewport_hud.py`).
- Sits centered inside `#09090B` studio canvas with `24px` outer breathing margin and a
  subtle `1px solid #22222A` frame.
- NO floating Histogram or MIC VU boxes blocking the video by default (`show_corner_hud = False`).
- Supports optional Rule-of-Thirds Grid, Cinema Widescreen Bars (2.35:1), Screen Flash,
  Countdown Timer, and Mouse Wheel / Drag PTZ.
"""

from typing import Dict, Any, Optional
import numpy as np
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QImage,
    QPainterPath,
    QMouseEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import QWidget


class ViewportCanvas(QWidget):
    ptz_changed = pyqtSignal(float, float, float)
    ptz_reset_requested = pyqtSignal()
    flash_peak_reached = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #09090B;")

        self._qimage: Optional[QImage] = None
        self._histogram: Dict[str, np.ndarray] = {}

        self._is_recording: bool = False
        self._is_virtual_cam: bool = False

        # Audio VU state (only shown if show_corner_hud is explicitly True)
        self._rms_db: float = -60.0
        self._peak_db: float = -60.0
        self._mic_available: bool = False

        # Default OFF so viewport stays 100% unobstructed on launch
        self.show_grid: bool = False
        self.show_cinema_bars: bool = False
        self.show_corner_hud: bool = False

        self._dragging: bool = False
        self._last_mouse_pos: QPointF = QPointF(0.0, 0.0)
        self._target_zoom: float = 1.00
        self._target_pan_x: float = 0.00
        self._target_pan_y: float = 0.00

        self._countdown_value: int = 0

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
        if self.show_corner_hud:
            self.update()

    def set_countdown(self, val: int) -> None:
        self._countdown_value = int(val)
        self.update()

    def trigger_softbox_flash(self) -> None:
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
        self._qimage = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self._histogram = telemetry.get("histogram", {})
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta != 0:
            step = 0.06 if delta > 0 else -0.06
            self._target_zoom = max(1.00, min(2.50, round(self._target_zoom + step, 2)))
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
            dx = (pos.x() - self._last_mouse_pos.x()) / max(120.0, float(self.width()) * 0.35)
            dy = (pos.y() - self._last_mouse_pos.y()) / max(120.0, float(self.height()) * 0.35)
            self._last_mouse_pos = pos
            self._target_pan_x = max(-1.0, min(1.0, self._target_pan_x - dx))
            self._target_pan_y = max(-1.0, min(1.0, self._target_pan_y - dy))
            self.ptz_changed.emit(self._target_zoom, self._target_pan_x, self._target_pan_y)
            event.accept()
            return
        self.setCursor(Qt.CursorShape.OpenHandCursor if self._target_zoom > 1.01 else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor if self._target_zoom > 1.01 else Qt.CursorShape.ArrowCursor)
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

    def _compute_video_rect(self) -> QRectF:
        pad = 24.0  # 24px outer breathing margin
        avail_w = max(64.0, float(self.width()) - pad * 2.0)
        avail_h = max(36.0, float(self.height()) - pad * 2.0)
        aspect = 16.0 / 9.0
        if avail_w / avail_h > aspect:
            vh = avail_h
            vw = vh * aspect
        else:
            vw = avail_w
            vh = vw / aspect
        return QRectF((float(self.width()) - vw) * 0.5, (float(self.height()) - vh) * 0.5, vw, vh)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), QColor("#09090B"))
        vrect = self._compute_video_rect()

        if self._qimage is not None:
            painter.drawImage(vrect, self._qimage)
        else:
            painter.fillRect(vrect, QColor("#111115"))

        # Optional Cinema Widescreen Bars (2.35:1)
        if self.show_cinema_bars:
            target_h = vrect.width() / 2.35
            if target_h < vrect.height():
                bar_h = (vrect.height() - target_h) * 0.5
                matte = QColor(0, 0, 0, 225)
                painter.fillRect(QRectF(vrect.x(), vrect.y(), vrect.width(), bar_h), matte)
                painter.fillRect(QRectF(vrect.x(), vrect.bottom() - bar_h, vrect.width(), bar_h), matte)

        # Optional Rule of Thirds Grid
        if self.show_grid:
            painter.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
            for frac in (1.0 / 3.0, 2.0 / 3.0):
                gx = vrect.x() + vrect.width() * frac
                gy = vrect.y() + vrect.height() * frac
                painter.drawLine(QPointF(gx, vrect.y()), QPointF(gx, vrect.bottom()))
                painter.drawLine(QPointF(vrect.x(), gy), QPointF(vrect.right(), gy))

        # Subtle 1px solid #22222A frame (or crimson/emerald when recording/virtual cam)
        if self._is_recording:
            border_col = QColor("#E11D48")
            border_w = 2.0
        elif self._is_virtual_cam:
            border_col = QColor("#10B981")
            border_w = 2.0
        else:
            border_col = QColor("#22222A")
            border_w = 1.0

        painter.setPen(QPen(border_col, border_w))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(vrect)

        # Optional Corner Histogram & Mic Meter (OFF by default)
        if self.show_corner_hud:
            self._draw_corner_hud(painter, vrect)

        if self._countdown_value > 0:
            cx, cy = vrect.center().x(), vrect.center().y()
            c_rect = QRectF(cx - 54.0, cy - 54.0, 108.0, 108.0)
            painter.setPen(QPen(QColor("#E5A93C"), 2.5))
            painter.setBrush(QColor(13, 13, 16, 205))
            painter.drawEllipse(c_rect)
            painter.setFont(QFont("Consolas", 42, QFont.Weight.Bold))
            painter.setPen(QColor("#F4F4F6"))
            painter.drawText(c_rect, Qt.AlignmentFlag.AlignCenter, str(self._countdown_value))

        if self._flash_alpha > 0.005:
            painter.fillRect(self.rect(), QColor(255, 253, 248, int(round(self._flash_alpha * 255))))

        painter.end()

    def _draw_corner_hud(self, painter: QPainter, vrect: QRectF) -> None:
        painter.save()
        hx, hy, hw, hh = vrect.x() + 16.0, vrect.y() + 16.0, 170.0, 78.0
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        painter.setBrush(QColor(13, 13, 16, 190))
        painter.drawRoundedRect(QRectF(hx, hy, hw, hh), 6.0, 6.0)

        plot_x, plot_y, plot_w, plot_h = hx + 8.0, hy + 8.0, hw - 16.0, hh - 16.0
        for key, col in [("b", QColor("#0A84FF")), ("g", QColor("#32D74B")), ("r", QColor("#FF453A")), ("luma", QColor("#F4F4F6"))]:
            arr = self._histogram.get(key)
            if arr is None or len(arr) == 0:
                continue
            path = QPainterPath()
            for i, val in enumerate(arr):
                px = plot_x + (i / float(len(arr) - 1)) * plot_w
                py = plot_y + plot_h - float(val) * plot_h
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            painter.setPen(QPen(col, 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # Compact VU meter at bottom-left
        vx, vy, vw, vh = vrect.x() + 16.0, vrect.bottom() - 44.0, 190.0, 28.0
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        painter.setBrush(QColor(13, 13, 16, 190))
        painter.drawRoundedRect(QRectF(vx, vy, vw, vh), 6.0, 6.0)
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#A1A1AA"))
        painter.drawText(QRectF(vx + 8.0, vy, 32.0, vh), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "MIC")
        norm_rms = float(np.clip((self._rms_db + 60.0) / 60.0, 0.0, 1.0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#272730"))
        painter.drawRoundedRect(QRectF(vx + 40.0, vy + 11.0, 100.0, 6.0), 2.0, 2.0)
        painter.setBrush(QColor("#10B981"))
        painter.drawRoundedRect(QRectF(vx + 40.0, vy + 11.0, 100.0 * norm_rms, 6.0), 2.0, 2.0)
        painter.setPen(QColor("#E5A93C"))
        painter.drawText(QRectF(vx + 144.0, vy, 40.0, vh), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{self._rms_db:3.0f}dB")
        painter.restore()
