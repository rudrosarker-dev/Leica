# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — DSLR / Cinema EVF Viewfinder Canvas (`ui/viewport_hud.py`).

LAW 2 & SECTION 3.3 COMPLIANCE:
- Frames the live video inside a sunken matte bezel with crisp camera viewfinder corner brackets
  (`20px` L-shaped corner reticles in `#E5A93C`) and a sleek bottom EVF Optical Status Strip
  (`SHUTTER | ISO/GAIN | WB KELVIN | FPS | CODEC | AUDIO VU`).
- Supports 16:9 and 9:16 aspect framing, Rule of Thirds Grid, 2.35:1 Cinema Scope Bars,
  Corner RGB Histogram, Softbox Flash, Countdown Timer, and Mouse Wheel / Drag PTZ.
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


class AudioVUPeakMeterWidget(QWidget):
    """
    Live compact Audio VU Peak Meter (-60dB to 0dB LED segments) + 50Hz Anti-Flicker Status
    docked in the Bottom EVF Glass Bar.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(210, 38)
        self._rms_db: float = -54.0
        self._peak_db: float = -48.0
        self._mic_available: bool = False

    def set_levels(self, rms_db: float, peak_db: float, mic_available: bool) -> None:
        self._rms_db = float(rms_db)
        self._peak_db = float(peak_db)
        self._mic_available = bool(mic_available)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = float(self.width()), float(self.height())
        box = QRectF(0.5, 2.0, w - 1.0, h - 4.0)
        painter.setPen(QPen(QColor("#262634"), 1.0))
        painter.setBrush(QColor("#08080B"))
        painter.drawRoundedRect(box, 4.0, 4.0)

        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#A1A1B0"))
        painter.drawText(QRectF(8.0, 4.0, 40.0, 14.0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "AUDIO")

        painter.setPen(QColor("#10B981"))
        painter.drawText(
            QRectF(w - 92.0, 4.0, 84.0, 14.0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "50Hz LOCKED",
        )

        # 16 Segmented LEDs from -60dB to 0dB
        num_segs = 16
        seg_x0 = 8.0
        seg_y = 20.0
        seg_w = (w - 58.0) / num_segs - 2.0
        seg_h = 8.0

        norm_rms = float(np.clip((self._rms_db + 60.0) / 60.0, 0.0, 1.0))
        active_segs = int(round(norm_rms * num_segs))

        for i in range(num_segs):
            sx = seg_x0 + i * (seg_w + 2.0)
            srect = QRectF(sx, seg_y, seg_w, seg_h)
            if i < active_segs:
                if i >= 14:
                    col = QColor("#E11D48")
                elif i >= 11:
                    col = QColor("#E5A93C")
                else:
                    col = QColor("#10B981")
            else:
                col = QColor("#1D1D26")
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(col)
            painter.drawRoundedRect(srect, 1.2, 1.2)

        painter.setPen(QColor("#E5A93C"))
        painter.drawText(
            QRectF(w - 46.0, 17.0, 40.0, 14.0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{self._rms_db:3.0f}dB",
        )
        painter.end()


class ViewportCanvas(QWidget):
    """
    DSLR / Cinema EVF Viewfinder Canvas:
    - Sunken matte bezel (`#050507`) with `20px` L-shaped corner reticles in `#E5A93C`.
    - Bottom EVF Optical Status Strip (`SHUTTER | ISO/GAIN | WB KELVIN | FPS | CODEC | AUDIO VU`).
    - Optional Rule-of-Thirds Grid, 2.35:1 Cinema Scope Bars, Corner RGB Histogram, and PTZ mouse control.
    """

    ptz_changed = pyqtSignal(float, float, float)
    ptz_reset_requested = pyqtSignal()
    flash_peak_reached = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #07070A;")

        self._qimage: Optional[QImage] = None
        self._histogram: Dict[str, np.ndarray] = {}
        self._fps: float = 30.0
        self._shutter_ev: int = -4
        self._iso_gain: int = 130
        self._wb_kelvin: int = 5500

        self._is_recording: bool = False
        self._is_virtual_cam: bool = False
        self._aspect_mode: str = "16:9"

        self._rms_db: float = -54.0
        self._peak_db: float = -48.0
        self._mic_available: bool = False

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

    def set_aspect_mode(self, mode: str) -> None:
        self._aspect_mode = "9:16" if "9:16" in mode else "16:9"
        self.update()

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
        self._fps = float(telemetry.get("fps", 30.0))
        self._shutter_ev = int(telemetry.get("exposure_ev", -4))
        self._iso_gain = int(telemetry.get("gain_iso", 130))
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta != 0:
            step = 0.06 if delta > 0 else -0.06
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
        pad_x = 20.0
        pad_top = 18.0
        pad_bottom = 38.0  # Space for sleek bottom EVF Optical Status Strip
        avail_w = max(64.0, float(self.width()) - pad_x * 2.0)
        avail_h = max(36.0, float(self.height()) - pad_top - pad_bottom)
        aspect = (9.0 / 16.0) if self._aspect_mode == "9:16" else (16.0 / 9.0)
        if avail_w / avail_h > aspect:
            vh = avail_h
            vw = vh * aspect
        else:
            vw = avail_w
            vh = vw / aspect
        vx = (float(self.width()) - vw) * 0.5
        vy = pad_top + (avail_h - vh) * 0.5
        return QRectF(vx, vy, vw, vh)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Sunken studio matte box background
        painter.fillRect(self.rect(), QColor("#07070A"))
        vrect = self._compute_video_rect()

        # Recessed outer bezel around EVF frame
        bezel_rect = vrect.adjusted(-4.0, -4.0, 4.0, 4.0)
        painter.setPen(QPen(QColor("#1E1E28"), 1.0))
        painter.setBrush(QColor("#040406"))
        painter.drawRoundedRect(bezel_rect, 4.0, 4.0)

        if self._qimage is not None:
            painter.drawImage(vrect, self._qimage)
        else:
            painter.fillRect(vrect, QColor("#0E0E14"))

        # Optional 2.35:1 Cinema Scope Bars
        if self.show_cinema_bars:
            target_h = vrect.width() / 2.35
            if target_h < vrect.height():
                bar_h = (vrect.height() - target_h) * 0.5
                matte = QColor(4, 4, 6, 235)
                painter.fillRect(QRectF(vrect.x(), vrect.y(), vrect.width(), bar_h), matte)
                painter.fillRect(QRectF(vrect.x(), vrect.bottom() - bar_h, vrect.width(), bar_h), matte)
                painter.setPen(QPen(QColor(229, 169, 60, 110), 1.0))
                painter.drawLine(QPointF(vrect.x(), vrect.y() + bar_h), QPointF(vrect.right(), vrect.y() + bar_h))
                painter.drawLine(QPointF(vrect.x(), vrect.bottom() - bar_h), QPointF(vrect.right(), vrect.bottom() - bar_h))

        # Optional Rule of Thirds Grid
        if self.show_grid:
            painter.setPen(QPen(QColor(255, 255, 255, 75), 1.0))
            for frac in (1.0 / 3.0, 2.0 / 3.0):
                gx = vrect.x() + vrect.width() * frac
                gy = vrect.y() + vrect.height() * frac
                painter.drawLine(QPointF(gx, vrect.y()), QPointF(gx, vrect.bottom()))
                painter.drawLine(QPointF(vrect.x(), gy), QPointF(vrect.right(), gy))

        # Inner frame border (crimson tally when recording, emerald when virtual cam)
        if self._is_recording:
            border_col = QColor("#E11D48")
            border_w = 2.0
        elif self._is_virtual_cam:
            border_col = QColor("#10B981")
            border_w = 2.0
        else:
            border_col = QColor("#262634")
            border_w = 1.0

        painter.setPen(QPen(border_col, border_w))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(vrect)

        # LAW 2: Crisp 20px L-Shaped Camera Viewfinder Corner Reticle Brackets in #E5A93C
        self._draw_evf_corner_reticles(painter, vrect)

        # LAW 2: Sleek Bottom EVF Optical Status Strip (SHUTTER | ISO/GAIN | WB KELVIN | FPS | CODEC | AUDIO VU)
        self._draw_evf_optical_status_strip(painter, vrect)

        # Optional Corner RGB Histogram
        if self.show_corner_hud:
            self._draw_corner_hud(painter, vrect)

        if self._countdown_value > 0:
            cx, cy = vrect.center().x(), vrect.center().y()
            c_rect = QRectF(cx - 54.0, cy - 54.0, 108.0, 108.0)
            painter.setPen(QPen(QColor("#E5A93C"), 2.5))
            painter.setBrush(QColor(13, 13, 16, 215))
            painter.drawEllipse(c_rect)
            painter.setFont(QFont("Consolas", 42, QFont.Weight.Bold))
            painter.setPen(QColor("#F4F4F6"))
            painter.drawText(c_rect, Qt.AlignmentFlag.AlignCenter, str(self._countdown_value))

        if self._flash_alpha > 0.005:
            painter.fillRect(self.rect(), QColor(255, 253, 248, int(round(self._flash_alpha * 255))))

        painter.end()

    @staticmethod
    def _draw_evf_corner_reticles(painter: QPainter, vrect: QRectF) -> None:
        """Draws 20px L-shaped corner reticle brackets inside the EVF viewport in #E5A93C."""
        painter.save()
        arm = 20.0
        inset = 12.0
        x0 = vrect.left() + inset
        y0 = vrect.top() + inset
        x1 = vrect.right() - inset
        y1 = vrect.bottom() - inset

        pen = QPen(QColor("#E5A93C"), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)

        # Top-Left L
        painter.drawLine(QPointF(x0, y0), QPointF(x0 + arm, y0))
        painter.drawLine(QPointF(x0, y0), QPointF(x0, y0 + arm))
        # Top-Right L
        painter.drawLine(QPointF(x1 - arm, y0), QPointF(x1, y0))
        painter.drawLine(QPointF(x1, y0), QPointF(x1, y0 + arm))
        # Bottom-Left L
        painter.drawLine(QPointF(x0, y1 - arm), QPointF(x0, y1))
        painter.drawLine(QPointF(x0, y1), QPointF(x0 + arm, y1))
        # Bottom-Right L
        painter.drawLine(QPointF(x1 - arm, y1), QPointF(x1, y1))
        painter.drawLine(QPointF(x1, y1 - arm), QPointF(x1, y1))

        painter.restore()

    def _draw_evf_optical_status_strip(self, painter: QPainter, vrect: QRectF) -> None:
        """Draws the sleek bottom EVF Optical Status Strip docked immediately under the video frame."""
        painter.save()
        strip_rect = QRectF(vrect.left(), vrect.bottom() + 6.0, vrect.width(), 24.0)
        painter.setPen(QPen(QColor("#22222E"), 1.0))
        painter.setBrush(QColor("#0B0B10"))
        painter.drawRoundedRect(strip_rect, 3.0, 3.0)

        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#D4D4DF"))

        status_text = (
            f"SHUTTER: {self._shutter_ev} EV (1/30s)   |   "
            f"ISO/GAIN: {self._iso_gain}   |   "
            f"WB: {self._wb_kelvin}K   |   "
            f"FPS: {self._fps:4.1f}   |   "
            f"CODEC: MJPG 4:2:2   |   "
            f"AUDIO VU: {self._rms_db:3.0f} dBFS"
        )
        painter.drawText(strip_rect, Qt.AlignmentFlag.AlignCenter, status_text)
        painter.restore()

    def _draw_corner_hud(self, painter: QPainter, vrect: QRectF) -> None:
        painter.save()
        hx, hy, hw, hh = vrect.right() - 188.0, vrect.top() + 20.0, 168.0, 74.0
        painter.setPen(QPen(QColor("#3E3E50"), 1.0))
        painter.setBrush(QColor(10, 10, 14, 210))
        painter.drawRoundedRect(QRectF(hx, hy, hw, hh), 5.0, 5.0)

        plot_x, plot_y, plot_w, plot_h = hx + 8.0, hy + 8.0, hw - 16.0, hh - 16.0
        for key, col in [
            ("b", QColor("#0EA5E9")),
            ("g", QColor("#10B981")),
            ("r", QColor("#F43F5E")),
            ("luma", QColor("#E5A93C")),
        ]:
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

        painter.restore()
