# -*- coding: utf-8 -*-
"""
Minimalist Spacious Studio Widgets (`ui/widgets.py`):
- Escapes `&` as `&&` in Qt labels/buttons so Qt never turns `&` into an underscore mnemonic!
- `PrecisionSlider`: Spacious 46px slider with double-click reset and Shift-scroll protection.
- `ToggleSwitch`: Clean pill toggle switch.
- `SegmentedBar`: 4-Tab sidebar header or 2-option selector.
- `ShutterButton`: 50x50px clean white circle shutter button.
- `RecordButton`: 50x50px clean crimson circle morphing into a rounded square when recording.
"""

from typing import List, Optional
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPainterPath,
    QMouseEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QAbstractButton,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
)

from ui.styles import draw_aperture_icon, draw_refresh_icon


def escape_qt_mnemonic(text: str) -> str:
    """Escapes single `&` into `&&` so Qt widgets render literal ampersands instead of underlines."""
    return text.replace("&&", "&").replace("&", "&&")


class CustomGrooveSlider(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(
        self,
        min_val: float,
        max_val: float,
        default_val: float,
        step: float = 1.0,
        bipolar: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.default_val = float(default_val)
        self.step = max(1e-4, float(step))
        self.bipolar = bool(bipolar)
        self._value = float(default_val)

        self._hovered = False
        self._dragging = False
        self.setFixedHeight(22)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, val: float, emit_signal: bool = False) -> None:
        clamped = max(self.min_val, min(self.max_val, float(val)))
        steps = round((clamped - self.min_val) / self.step)
        snapped = max(self.min_val, min(self.max_val, self.min_val + steps * self.step))
        if abs(snapped - self._value) > 1e-6:
            self._value = snapped
            self.update()
            if emit_signal:
                self.valueChanged.emit(self._value)

    def reset_to_default(self) -> None:
        self.set_value(self.default_val, emit_signal=True)

    def _pos_to_value(self, x_px: float) -> float:
        pad = 8.0
        usable_w = max(1.0, self.width() - pad * 2.0)
        norm = max(0.0, min(1.0, (x_px - pad) / usable_w))
        return self.min_val + norm * (self.max_val - self.min_val)

    def _value_to_pos(self, val: float) -> float:
        pad = 8.0
        usable_w = max(1.0, self.width() - pad * 2.0)
        span = max(1e-6, self.max_val - self.min_val)
        norm = max(0.0, min(1.0, (val - self.min_val) / span))
        return pad + norm * usable_w

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset_to_default()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.set_value(self._pos_to_value(event.position().x()), emit_signal=True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self.set_value(self._pos_to_value(event.position().x()), emit_signal=True)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta != 0:
            self.set_value(self._value + (1.0 if delta > 0 else -1.0) * self.step, emit_signal=True)
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        cy = h * 0.5
        pad = 8.0
        groove_h = 4.0

        groove_rect = QRectF(pad, cy - groove_h * 0.5, w - pad * 2.0, groove_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#272730"))
        painter.drawRoundedRect(groove_rect, 2.0, 2.0)

        handle_x = self._value_to_pos(self._value)
        amber = QColor("#E5A93C")

        if self.bipolar and self.min_val < 0.0 < self.max_val:
            zero_x = self._value_to_pos(0.0)
            painter.setPen(QPen(QColor("#52525B"), 1.0))
            painter.drawLine(QPointF(zero_x, cy - 5.0), QPointF(zero_x, cy + 5.0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(amber)
            left_x, right_x = min(zero_x, handle_x), max(zero_x, handle_x)
            if right_x - left_x > 0.5:
                painter.drawRoundedRect(QRectF(left_x, cy - groove_h * 0.5, right_x - left_x, groove_h), 1.5, 1.5)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(amber)
            fill_w = max(0.0, handle_x - pad)
            if fill_w > 0.5:
                painter.drawRoundedRect(QRectF(pad, cy - groove_h * 0.5, fill_w, groove_h), 2.0, 2.0)

        fill_col = amber if (self._hovered or self._dragging) else QColor("#F4F4F6")
        painter.setPen(QPen(QColor("#111115"), 2.0))
        painter.setBrush(fill_col)
        painter.drawEllipse(QPointF(handle_x, cy), 7.0, 7.0)
        painter.end()


class PrecisionSlider(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(
        self,
        title: str,
        min_val: float,
        max_val: float,
        default_val: float,
        step: float = 1.0,
        decimals: int = 0,
        suffix: str = "",
        bipolar: bool = False,
        show_plus: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.decimals = int(decimals)
        self.suffix = suffix
        self.bipolar = bipolar
        self.show_plus = show_plus or bipolar

        self.setFixedHeight(46)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(escape_qt_mnemonic(title))
        self.title_label.setStyleSheet("color: #A1A1AA; font-size: 12px; font-weight: 400;")

        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setStyleSheet(
            'color: #E5A93C; font-family: "Consolas", "JetBrains Mono", monospace; font-size: 11px; font-weight: 600;'
        )

        top_row.addWidget(self.title_label)
        top_row.addStretch(1)
        top_row.addWidget(self.value_label)

        self.slider = CustomGrooveSlider(min_val, max_val, default_val, step=step, bipolar=bipolar, parent=self)
        self.slider.valueChanged.connect(self._on_slider_changed)

        layout.addLayout(top_row)
        layout.addWidget(self.slider)
        self._update_value_text(default_val)

    def _format_val(self, val: float) -> str:
        if abs(val) < 1e-6:
            val = 0.0
        num_str = f"{int(round(val))}" if self.decimals == 0 else f"{val:.{self.decimals}f}"
        if self.show_plus and val > 1e-5:
            num_str = "+" + num_str
        return f"{num_str}{self.suffix}"

    def _update_value_text(self, val: float) -> None:
        self.value_label.setText(self._format_val(val))

    def _on_slider_changed(self, val: float) -> None:
        self._update_value_text(val)
        self.valueChanged.emit(val)

    def value(self) -> float:
        return self.slider.value

    def setValue(self, val: float, emit_signal: bool = False) -> None:
        self.slider.set_value(val, emit_signal=emit_signal)
        self._update_value_text(self.slider.value)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.slider.reset_to_default()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class ToggleSwitch(QAbstractButton):
    def __init__(self, label_text: str, checked: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._display_text = label_text
        self.setText(escape_qt_mnemonic(label_text))
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(280, 26)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        hovered = self.underMouse()

        text_color = QColor("#F4F4F6") if (self.isChecked() or hovered) else QColor("#A1A1AA")
        painter.setPen(text_color)
        font = self.font()
        font.setPixelSize(12)
        font.setWeight(500 if self.isChecked() else 400)
        painter.setFont(font)
        painter.drawText(
            QRectF(0.0, 0.0, w - 44.0, h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._display_text,
        )

        sw_w, sw_h = 36.0, 20.0
        sw_x = w - sw_w - 2.0
        sw_y = (h - sw_h) * 0.5
        pill_rect = QRectF(sw_x, sw_y, sw_w, sw_h)

        if self.isChecked():
            painter.setPen(QPen(QColor("#E5A93C"), 1.0))
            painter.setBrush(QColor(229, 169, 60, 68))
        else:
            painter.setPen(QPen(QColor("#2C2C38"), 1.0))
            painter.setBrush(QColor("#1C1C24"))

        painter.drawRoundedRect(pill_rect, 10.0, 10.0)

        knob_x = (sw_x + sw_w - 10.0) if self.isChecked() else (sw_x + 10.0)
        knob_y = sw_y + sw_h * 0.5
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E5A93C") if self.isChecked() else QColor("#71717A"))
        painter.drawEllipse(QPointF(knob_x, knob_y), 6.5, 6.5)
        painter.end()


class SegmentedBar(QWidget):
    indexChanged = pyqtSignal(int)

    def __init__(self, labels: List[str], height: int = 36, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.labels = labels
        self._current_index = 0
        self._buttons: List[QPushButton] = []

        self.setFixedHeight(height)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for idx, text in enumerate(labels):
            btn = QPushButton(escape_qt_mnemonic(text))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.clicked.connect(lambda checked, i=idx: self.set_current_index(i, emit_signal=True))
            layout.addWidget(btn)
            self._buttons.append(btn)

        self.set_current_index(0, emit_signal=False)

    def current_index(self) -> int:
        return self._current_index

    def set_current_index(self, index: int, emit_signal: bool = False) -> None:
        if not (0 <= index < len(self._buttons)):
            return
        self._current_index = index
        for i, btn in enumerate(self._buttons):
            active = i == index
            btn.setChecked(active)
            if active:
                btn.setStyleSheet(
                    "background-color: #262118; border: 1px solid #E5A93C; border-radius: 6px; "
                    "color: #E5A93C; font-size: 11px; font-weight: 600; padding: 2px 6px;"
                )
            else:
                btn.setStyleSheet(
                    "background-color: #18181E; border: 1px solid #24242C; border-radius: 6px; "
                    "color: #A1A1AA; font-size: 11px; font-weight: 500; padding: 2px 6px;"
                )
        if emit_signal:
            self.indexChanged.emit(index)


class ShutterButton(QPushButton):
    """Primary Photo Shutter Button (50x50px clean white circle)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Capture Photo")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        center = QPointF(self.width() * 0.5, self.height() * 0.5)
        hovered = self.underMouse()
        pressed = self.isDown()

        outer_col = QColor("#E5A93C") if hovered else QColor("#F4F4F6")
        painter.setPen(QPen(outer_col, 2.0))
        painter.setBrush(QColor("#0D0D10"))
        painter.drawEllipse(center, 22.0, 22.0)

        inner_r = 16.0 if pressed else 18.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E5A93C") if hovered else QColor("#F4F4F6"))
        painter.drawEllipse(center, inner_r, inner_r)
        painter.end()


class RecordButton(QPushButton):
    """Primary Video Record Button (50x50px clean crimson circle, morphs to square when recording)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Start / Stop Video Recording")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() * 0.5, self.height() * 0.5
        center = QPointF(cx, cy)
        recording = self.isChecked()
        hovered = self.underMouse()

        ring_col = QColor("#E11D48") if (recording or hovered) else QColor("#71717A")
        painter.setPen(QPen(ring_col, 2.0))
        painter.setBrush(QColor("#0D0D10"))
        painter.drawEllipse(center, 22.0, 22.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E11D48"))
        if recording:
            painter.drawRoundedRect(QRectF(cx - 9.0, cy - 9.0, 18.0, 18.0), 4.0, 4.0)
        else:
            painter.drawEllipse(center, 15.0 if self.isDown() else 16.5, 15.0 if self.isDown() else 16.5)
        painter.end()


class PauseRecordButton(QPushButton):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(34, 34)
        self.setCheckable(True)
        self.setEnabled(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() * 0.5, self.height() * 0.5
        painter.setPen(QPen(QColor("#3E3E4E"), 1.5))
        painter.setBrush(QColor("#1C1C24"))
        painter.drawEllipse(QPointF(cx, cy), 15.5, 15.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F4F4F6"))
        painter.drawRoundedRect(QRectF(cx - 4.5, cy - 5.5, 3.0, 11.0), 1.0, 1.0)
        painter.drawRoundedRect(QRectF(cx + 1.5, cy - 5.5, 3.0, 11.0), 1.0, 1.0)
        painter.end()


class ApertureLogoWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(22, 22)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        draw_aperture_icon(
            painter,
            QRectF(1.0, 1.0, float(self.width() - 2), float(self.height() - 2)),
            QColor("#E5A93C"),
        )
        painter.end()


class RefreshIconButton(QPushButton):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Refresh Camera List")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        col = QColor("#E5A93C") if self.underMouse() else QColor("#F4F4F6")
        draw_refresh_icon(painter, QRectF(0, 0, float(self.width()), float(self.height())), col)
        painter.end()


class InspectorCard(QFrame):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("InspectorCard")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 12, 14, 14)
        self.main_layout.setSpacing(12)

        header = QLabel(escape_qt_mnemonic(title.upper()))
        header.setObjectName("SectionHeaderLabel")
        self.main_layout.addWidget(header)

    def add_widget(self, widget: QWidget) -> None:
        self.main_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.main_layout.addLayout(layout)
