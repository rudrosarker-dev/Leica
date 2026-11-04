# -*- coding: utf-8 -*-
"""
Custom Precision Industrial Widgets (`ui/widgets.py`):
- `PrecisionSlider`: Compound parameter label + numeric readout + `CustomGrooveSlider`
  with bipolar/unipolar fill, double-click reset to default_value, and Shift-scroll protection.
- `ToggleSwitch`: Custom painted animated hardware toggle switch.
- `SegmentedBar`: Custom 2-button or 3-tab segmented selector.
- `ShutterButton`: Custom QPainter 52x52px tactile still shutter release button.
- `RecordButton`: Custom QPainter 52x52px cinema record button morphing circle -> square.
- `PauseRecordButton`: Custom QPainter 36x36px pause/resume transport button.
- `InspectorCard`: Styled #15151B studio section container.
"""

from typing import List, Optional
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
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


class CustomGrooveSlider(QWidget):
    """
    Custom QPainter horizontal slider supporting:
    - Bipolar (center-0 outward fill) and Unipolar (left-to-handle fill) in #E5A93C
    - Double-click anywhere on groove/handle to reset to `default_value`
    - Scroll-wheel ignore unless Shift is held or widget explicitly has focus
    """

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
        self.setFixedHeight(20)
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
        # Scroll-wheel protection: ignore wheel unless Shift is held so QScrollArea scrolls cleanly
        modifiers = event.modifiers()
        if not (modifiers & Qt.KeyboardModifier.ShiftModifier):
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta != 0:
            direction = 1.0 if delta > 0 else -1.0
            self.set_value(self._value + direction * self.step, emit_signal=True)
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        cy = h * 0.5
        pad = 8.0
        groove_h = 4.0

        # Track background groove (#262630)
        groove_rect = QRectF(pad, cy - groove_h * 0.5, w - pad * 2.0, groove_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#262630"))
        painter.drawRoundedRect(groove_rect, 2.0, 2.0)

        handle_x = self._value_to_pos(self._value)
        amber = QColor("#E5A93C")

        if self.bipolar and self.min_val < 0.0 < self.max_val:
            zero_x = self._value_to_pos(0.0)
            # Center 0 tick mark
            painter.setPen(QPen(QColor("#71717A"), 1.0))
            painter.drawLine(QPointF(zero_x, cy - 5.0), QPointF(zero_x, cy + 5.0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(amber)
            left_x = min(zero_x, handle_x)
            right_x = max(zero_x, handle_x)
            if right_x - left_x > 0.5:
                fill_rect = QRectF(left_x, cy - groove_h * 0.5, right_x - left_x, groove_h)
                painter.drawRoundedRect(fill_rect, 1.5, 1.5)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(amber)
            fill_w = max(0.0, handle_x - pad)
            if fill_w > 0.5:
                fill_rect = QRectF(pad, cy - groove_h * 0.5, fill_w, groove_h)
                painter.drawRoundedRect(fill_rect, 2.0, 2.0)

        # Handle: 14x14px anti-aliased circle (#F4F4F6 idle, #E5A93C hover/drag, 2px #0E0E12 ring)
        handle_r = 7.0
        fill_col = amber if (self._hovered or self._dragging) else QColor("#F4F4F6")
        painter.setPen(QPen(QColor("#0E0E12"), 2.0))
        painter.setBrush(fill_col)
        painter.drawEllipse(QPointF(handle_x, cy), handle_r, handle_r)
        painter.end()


class PrecisionSlider(QWidget):
    """
    Compound widget (Fixed Height: 44px):
    - Top Row: Parameter Title (#9CA3AF -> #F4F4F6 on hover) + Formatted Readout (Consolas 11px #E5A93C)
    - Bottom Row: CustomGrooveSlider with double-click reset on both labels and groove.
    """

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

        self.setFixedHeight(44)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: 400;")

        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setStyleSheet(
            'color: #E5A93C; font-family: "Consolas", "JetBrains Mono", monospace; '
            "font-size: 11px; font-weight: 600;"
        )

        top_row.addWidget(self.title_label)
        top_row.addStretch(1)
        top_row.addWidget(self.value_label)

        self.slider = CustomGrooveSlider(
            min_val=min_val,
            max_val=max_val,
            default_val=default_val,
            step=step,
            bipolar=bipolar,
            parent=self,
        )
        self.slider.valueChanged.connect(self._on_slider_changed)

        layout.addLayout(top_row)
        layout.addWidget(self.slider)

        self._update_value_text(default_val)

    def _format_val(self, val: float) -> str:
        if abs(val) < 1e-6:
            val = 0.0
        if self.decimals == 0:
            num_str = f"{int(round(val))}"
        else:
            num_str = f"{val:.{self.decimals}f}"
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

    def enterEvent(self, event) -> None:
        self.title_label.setStyleSheet("color: #F4F4F6; font-size: 11px; font-weight: 500;")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.title_label.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: 400;")
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.slider.reset_to_default()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class ToggleSwitch(QAbstractButton):
    """
    Industrial Leica/Resolve custom toggle switch with text label and animated pill indicator.
    """

    def __init__(self, label_text: str, checked: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText(label_text)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(260, 24)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        hovered = self.underMouse()

        # Label on left
        text_color = QColor("#F4F4F6") if (self.isChecked() or hovered) else QColor("#9CA3AF")
        painter.setPen(text_color)
        font = self.font()
        font.setPixelSize(11)
        font.setWeight(500 if self.isChecked() else 400)
        painter.setFont(font)
        text_rect = QRectF(0.0, 0.0, w - 42.0, h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())

        # Switch pill on right (34x18px)
        sw_w = 34.0
        sw_h = 18.0
        sw_x = w - sw_w - 2.0
        sw_y = (h - sw_h) * 0.5
        pill_rect = QRectF(sw_x, sw_y, sw_w, sw_h)

        if self.isChecked():
            painter.setPen(QPen(QColor("#E5A93C"), 1.0))
            painter.setBrush(QColor(229, 169, 60, 64))
        else:
            painter.setPen(QPen(QColor("#2C2C38"), 1.0))
            painter.setBrush(QColor("#1C1C24"))

        painter.drawRoundedRect(pill_rect, 9.0, 9.0)

        # Thumb knob (12x12px)
        knob_r = 6.0
        knob_x = (sw_x + sw_w - 9.0) if self.isChecked() else (sw_x + 9.0)
        knob_y = sw_y + sw_h * 0.5
        knob_col = QColor("#E5A93C") if self.isChecked() else QColor("#71717A")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob_col)
        painter.drawEllipse(QPointF(knob_x, knob_y), knob_r, knob_r)
        painter.end()


class SegmentedBar(QWidget):
    """Sleek segmented button bar for 2-mode ISP switch or 3-tab Right Dock navigation."""

    indexChanged = pyqtSignal(int)

    def __init__(self, labels: List[str], height: int = 32, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.labels = labels
        self._current_index = 0
        self._buttons: List[QPushButton] = []

        self.setFixedHeight(height)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        for idx, text in enumerate(labels):
            btn = QPushButton(text)
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
                    "background-color: #262118; border: 1px solid #E5A93C; "
                    "color: #E5A93C; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;"
                )
            else:
                btn.setStyleSheet(
                    "background-color: #15151B; border: 1px solid #22222B; "
                    "color: #9CA3AF; font-size: 10px; font-weight: 600; letter-spacing: 0.8px;"
                )
        if emit_signal:
            self.indexChanged.emit(index)


class ShutterButton(QPushButton):
    """
    Primary Still Photo Shutter Release Button (52x52px):
    Draws outer 2px ring #F4F4F6 (48x48px), inner solid #F4F4F6 circle (38x38px,
    turns #E5A93C on hover, shrinks to 34x34px on mouse press).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Capture Still Frame (Shutter Release)")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center = QPointF(self.width() * 0.5, self.height() * 0.5)
        hovered = self.underMouse()
        pressed = self.isDown()

        # Outer 2px ring (48x48px -> radius 23)
        outer_col = QColor("#E5A93C") if hovered else QColor("#F4F4F6")
        painter.setPen(QPen(outer_col, 2.0))
        painter.setBrush(QColor("#0A0A0D"))
        painter.drawEllipse(center, 23.0, 23.0)

        # Inner solid circle (38x38px -> radius 19, or 34x34px -> radius 17 on press)
        inner_r = 17.0 if pressed else 19.0
        inner_col = QColor("#E5A93C") if hovered else QColor("#F4F4F6")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(inner_col)
        painter.drawEllipse(center, inner_r, inner_r)
        painter.end()


class RecordButton(QPushButton):
    """
    Primary Cinema Record Button (52x52px):
    Draws outer 2px ring #71717A (#E11D48 when recording), inner 34x34px circle #E11D48
    when idle; morphs into a 20x20px rounded crimson square (4px radius) when recording is active.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Start / Stop Master MP4 Recording")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cx = self.width() * 0.5
        cy = self.height() * 0.5
        center = QPointF(cx, cy)
        recording = self.isChecked()
        hovered = self.underMouse()

        ring_col = QColor("#E11D48") if (recording or hovered) else QColor("#71717A")
        painter.setPen(QPen(ring_col, 2.0))
        painter.setBrush(QColor("#0A0A0D"))
        painter.drawEllipse(center, 23.0, 23.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E11D48"))

        if recording:
            sq_rect = QRectF(cx - 10.0, cy - 10.0, 20.0, 20.0)
            painter.drawRoundedRect(sq_rect, 4.0, 4.0)
        else:
            r = 15.5 if self.isDown() else 17.0
            painter.drawEllipse(center, r, r)
        painter.end()


class PauseRecordButton(QPushButton):
    """
    Custom QPainter 36x36px circular button drawing two crisp vertical pause bars (||)
    or a play triangle (>) when recording is paused.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCheckable(True)
        self.setEnabled(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Pause / Resume Active Recording")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cx = self.width() * 0.5
        cy = self.height() * 0.5
        enabled = self.isEnabled()
        paused = self.isChecked()

        border_col = QColor("#E5A93C") if paused else (QColor("#3E3E4E") if enabled else QColor("#22222B"))
        bg_col = QColor("#1C1C24") if enabled else QColor("#121217")
        fg_col = QColor("#E5A93C") if paused else (QColor("#F4F4F6") if enabled else QColor("#52525B"))

        painter.setPen(QPen(border_col, 1.5))
        painter.setBrush(bg_col)
        painter.drawEllipse(QPointF(cx, cy), 16.5, 16.5)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fg_col)

        if paused:
            # Draw play triangle
            path = QPainterPath()
            path.moveTo(cx - 4.0, cy - 6.0)
            path.lineTo(cx + 6.5, cy)
            path.lineTo(cx - 4.0, cy + 6.0)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            # Draw two vertical pause bars
            painter.drawRoundedRect(QRectF(cx - 5.0, cy - 6.0, 3.2, 12.0), 1.0, 1.0)
            painter.drawRoundedRect(QRectF(cx + 1.8, cy - 6.0, 3.2, 12.0), 1.0, 1.0)
        painter.end()


class ApertureLogoWidget(QWidget):
    """20x20px custom-painted Leica Aperture blade icon for Top Telemetry Bar."""

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
    """28x28px custom-painted circular refresh vector icon button."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Rescan USB UVC Camera Devices")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        col = QColor("#E5A93C") if self.underMouse() else QColor("#F4F4F6")
        draw_refresh_icon(painter, QRectF(0, 0, float(self.width()), float(self.height())), col)
        painter.end()


class InspectorCard(QFrame):
    """
    Elevated Card / Section Group container (#15151B with 6px radius and 1px solid #22222B border)
    featuring an uppercase #71717A section header.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("InspectorCard")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 10, 12, 12)
        self.main_layout.setSpacing(8)

        header = QLabel(title.upper())
        header.setObjectName("SectionHeaderLabel")
        self.main_layout.addWidget(header)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #22222B; border: none;")
        self.main_layout.addWidget(div)

    def add_widget(self, widget: QWidget) -> None:
        self.main_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.main_layout.addLayout(layout)
