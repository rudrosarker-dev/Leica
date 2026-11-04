# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — Tactile 3D / 2.5D Machined Camera Hardware Widgets (`ui/widgets.py`).

LAW 2 & SECTION 3.2 COMPLIANCE:
1. `TactileHardwareButton` (`HardwareButton`):
   - Vertical metallic gradient (`#262632` top to `#14141B` bottom; Hover `#2E2E3E` to `#1A1A24`;
     Pressed `#111117` to `#191922` with `+1px` physical travel).
   - `1px` top specular highlight (`#3E3E50` idle, `#E5A93C` active) + `1px` dark bottom bevel (`#08080B`).
   - Integrated 3D Glowing LED Indicator (`6x6px` / `7x7px` `QRadialGradient` `#10B981` emerald or `#E5A93C` amber when ON,
     recessed `#2A2A35` socket when OFF).
2. `MachinedFaderSlider` (`PrecisionHardwareSlider` / `PrecisionSlider`):
   - Height: 48px
   - Top row: Parameter Name (`#D4D4D8` 11px medium) + Value Readout Pill (`#101015` recessed box with `#E5A93C` Consolas 11px bold).
   - Bottom row: 11 engraved metallic ruler tick marks (`#323240`), recessed 5px groove (`#09090D`),
     illuminated amber light-pipe bar (`QLinearGradient` `#B47B18` to `#F5B945`), and 3D Machined Titanium Fader Cap
     (`16x20px` / `20x14px` brushed titanium gradient with glowing `#E5A93C` center index line).
   - Double-clicking resets to factory default.
3. `MechanicalShutterButton` & `CinemaRecordButton` (60x60px):
   - 3-layer 3D metallic bezel (`QConicalGradient` brushed steel outer ring, recessed dark well,
     and glossy 3D plunger that physically compresses on click; crimson tally halo on Record).
"""

from typing import List, Optional
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QMouseEvent,
    QWheelEvent,
    QLinearGradient,
    QRadialGradient,
    QConicalGradient,
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

from ui.styles import draw_lumixa_3d_lens, draw_refresh_icon


def escape_qt_mnemonic(text: str) -> str:
    """Escapes single `&` into `&&` so Qt widgets render literal ampersands instead of underlines."""
    return text.replace("&&", "&").replace("&", "&&")


class TactileHardwareButton(QPushButton):
    """
    3D Machined Camera Body Hardware Button with physical +1px travel and integrated 3D LED indicator dot.
    """

    def __init__(
        self,
        text: str = "",
        led_color: str = "amber",  # "amber" (#E5A93C), "emerald" (#10B981), "crimson" (#E11D48), or "none"
        checkable: bool = False,
        checked: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(escape_qt_mnemonic(text), parent)
        self._raw_text = text
        self.led_color = led_color
        self.setCheckable(checkable)
        if checkable:
            self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(32)

    def setText(self, text: str) -> None:
        self._raw_text = text
        super().setText(escape_qt_mnemonic(text))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        hovered = self.underMouse() and self.isEnabled()
        pressed = self.isDown() and self.isEnabled()
        checked = self.isChecked() and self.isCheckable()

        # 1. Outer drop shadow recess (#060608)
        outer_rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        painter.setPen(QPen(QColor("#060608"), 1.0))
        painter.setBrush(QColor("#060608"))
        painter.drawRoundedRect(outer_rect, 5.0, 5.0)

        # 2. 3D Machined Button Surface Gradient
        btn_rect = QRectF(1.0, 1.5 if pressed else 1.0, w - 2.0, h - 2.5)
        grad = QLinearGradient(0.0, btn_rect.top(), 0.0, btn_rect.bottom())
        if pressed:
            # Inverted gradient when depressed
            grad.setColorAt(0.0, QColor("#111117"))
            grad.setColorAt(1.0, QColor("#191922"))
        elif checked:
            if self.led_color == "emerald":
                grad.setColorAt(0.0, QColor("#152D26"))
                grad.setColorAt(1.0, QColor("#0D1C18"))
            else:
                grad.setColorAt(0.0, QColor("#2D2518"))
                grad.setColorAt(1.0, QColor("#18140E"))
        elif hovered:
            grad.setColorAt(0.0, QColor("#2E2E3E"))
            grad.setColorAt(1.0, QColor("#1A1A24"))
        else:
            grad.setColorAt(0.0, QColor("#262632"))
            grad.setColorAt(1.0, QColor("#14141B"))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawRoundedRect(btn_rect, 4.5, 4.5)

        # 3. Top 1px Specular Highlight & Bottom 1px Dark Bevel
        if checked:
            top_col = QColor("#10B981") if self.led_color == "emerald" else QColor("#E5A93C")
        elif hovered:
            top_col = QColor("#525268")
        else:
            top_col = QColor("#3E3E50")

        painter.setPen(QPen(top_col, 1.0))
        painter.drawLine(QPointF(btn_rect.left() + 4.0, btn_rect.top() + 0.5), QPointF(btn_rect.right() - 4.0, btn_rect.top() + 0.5))

        painter.setPen(QPen(QColor("#08080B"), 1.0))
        painter.drawLine(QPointF(btn_rect.left() + 3.0, btn_rect.bottom()), QPointF(btn_rect.right() - 3.0, btn_rect.bottom()))

        # Subtle side border
        border_col = top_col if checked else QColor("#2A2A36")
        painter.setPen(QPen(border_col, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(btn_rect, 4.5, 4.5)

        # 4. Integrated 3D Glowing LED Indicator (7x7px circular lamp)
        y_shift = 1.0 if pressed else 0.0
        show_led = self.isCheckable() or self.led_color in ("amber", "emerald", "crimson")
        text_left = 8.0

        if show_led and self.led_color != "none":
            led_cx = 13.0
            led_cy = h * 0.5 + y_shift
            led_r = 3.5

            if checked:
                if self.led_color == "emerald":
                    core_col = QColor("#34D399")
                    mid_col = QColor("#10B981")
                    halo_col = QColor(16, 185, 129, 95)
                elif self.led_color == "crimson":
                    core_col = QColor("#FB7185")
                    mid_col = QColor("#E11D48")
                    halo_col = QColor(225, 29, 72, 95)
                else:
                    core_col = QColor("#FDE68A")
                    mid_col = QColor("#E5A93C")
                    halo_col = QColor(229, 169, 60, 95)

                # Outer glow halo
                halo_grad = QRadialGradient(QPointF(led_cx, led_cy), led_r * 2.2)
                halo_grad.setColorAt(0.0, halo_col)
                halo_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(halo_grad)
                painter.drawEllipse(QPointF(led_cx, led_cy), led_r * 2.2, led_r * 2.2)

                # 3D LED Dome
                led_grad = QRadialGradient(QPointF(led_cx - 1.0, led_cy - 1.0), led_r * 1.2)
                led_grad.setColorAt(0.0, core_col)
                led_grad.setColorAt(0.65, mid_col)
                led_grad.setColorAt(1.0, QColor("#09090D"))
                painter.setPen(QPen(QColor("#09090D"), 0.8))
                painter.setBrush(led_grad)
                painter.drawEllipse(QPointF(led_cx, led_cy), led_r, led_r)
            else:
                # Recessed unlit LED socket (#2A2A35)
                sock_grad = QRadialGradient(QPointF(led_cx, led_cy), led_r)
                sock_grad.setColorAt(0.0, QColor("#2A2A35"))
                sock_grad.setColorAt(1.0, QColor("#121218"))
                painter.setPen(QPen(QColor("#08080B"), 1.0))
                painter.setBrush(sock_grad)
                painter.drawEllipse(QPointF(led_cx, led_cy), led_r, led_r)

            text_left = 24.0

        # 5. Button Label
        if not self.isEnabled():
            txt_col = QColor("#525260")
        elif checked:
            txt_col = QColor("#10B981") if self.led_color == "emerald" else QColor("#F5B945")
        elif hovered:
            txt_col = QColor("#FFFFFF")
        else:
            txt_col = QColor("#E4E4EC")

        painter.setPen(txt_col)
        font = self.font()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Bold if checked else QFont.Weight.DemiBold)
        painter.setFont(font)

        text_rect = QRectF(text_left, y_shift, w - text_left - 6.0, h)
        align = (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if (show_led and self.led_color != "none")
            else Qt.AlignmentFlag.AlignCenter
        )
        painter.drawText(text_rect, align, self._raw_text)
        painter.end()


# Explicit Law 2 alias
HardwareButton = TactileHardwareButton


class MachinedGrooveTrack(QWidget):
    """
    Custom painted broadcast fader track with:
    - 11 engraved metallic ruler tick marks (#323240)
    - Recessed 5px groove (#09090D)
    - Illuminated amber light-pipe bar (QLinearGradient #B47B18 to #F5B945)
    - 3D Machined Titanium Fader Cap (20x14px rounded bevel rectangle with glowing #E5A93C center index line)
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
        self.setFixedHeight(24)
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
        pad = 11.0
        usable_w = max(1.0, self.width() - pad * 2.0)
        norm = max(0.0, min(1.0, (x_px - pad) / usable_w))
        return self.min_val + norm * (self.max_val - self.min_val)

    def _value_to_pos(self, val: float) -> float:
        pad = 11.0
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
        pad = 11.0
        usable_w = max(1.0, w - pad * 2.0)

        # 1. 11 Engraved Metallic Ruler Tick Marks (#323240)
        for i in range(11):
            tx = pad + (i / 10.0) * usable_w
            is_major = i in (0, 5, 10)
            tick_h = 8.5 if is_major else 5.5
            painter.setPen(QPen(QColor("#48485A" if is_major else "#323240"), 1.0))
            painter.drawLine(QPointF(tx, cy - tick_h), QPointF(tx, cy + tick_h))

        # 2. Recessed 5px Groove (#09090D)
        groove_h = 5.0
        groove_rect = QRectF(pad, cy - groove_h * 0.5, usable_w, groove_h)
        painter.setPen(QPen(QColor("#262634"), 1.0))
        painter.setBrush(QColor("#09090D"))
        painter.drawRoundedRect(groove_rect, 2.5, 2.5)

        # 3. Active Illuminated Amber Light-Pipe Bar (QLinearGradient #B47B18 to #F5B945)
        handle_x = self._value_to_pos(self._value)
        pipe_grad = QLinearGradient(pad, 0.0, w - pad, 0.0)
        pipe_grad.setColorAt(0.0, QColor("#B47B18"))
        pipe_grad.setColorAt(1.0, QColor("#F5B945"))

        if self.bipolar and self.min_val < 0.0 < self.max_val:
            zero_x = self._value_to_pos(0.0)
            left_x, right_x = min(zero_x, handle_x), max(zero_x, handle_x)
            if right_x - left_x > 0.5:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(pipe_grad)
                painter.drawRoundedRect(QRectF(left_x, cy - groove_h * 0.5, right_x - left_x, groove_h), 2.0, 2.0)
        else:
            fill_w = max(0.0, handle_x - pad)
            if fill_w > 0.5:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(pipe_grad)
                painter.drawRoundedRect(QRectF(pad, cy - groove_h * 0.5, fill_w, groove_h), 2.0, 2.0)

        # 4. 3D Machined Titanium Fader Cap (20x14px rounded bevel rectangle + glowing #E5A93C center index line)
        cap_w, cap_h = 20.0, 14.0
        cap_rect = QRectF(handle_x - cap_w * 0.5, cy - cap_h * 0.5, cap_w, cap_h)

        # Drop shadow under fader cap
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 160))
        painter.drawRoundedRect(cap_rect.translated(0.0, 1.5), 3.0, 3.0)

        cap_grad = QLinearGradient(cap_rect.left(), cap_rect.top(), cap_rect.left(), cap_rect.bottom())
        if self._hovered or self._dragging:
            cap_grad.setColorAt(0.0, QColor("#4A4A5C"))
            cap_grad.setColorAt(0.5, QColor("#2E2E3C"))
            cap_grad.setColorAt(1.0, QColor("#181822"))
        else:
            cap_grad.setColorAt(0.0, QColor("#3E3E4E"))
            cap_grad.setColorAt(0.5, QColor("#252532"))
            cap_grad.setColorAt(1.0, QColor("#14141C"))

        painter.setPen(QPen(QColor("#525266" if (self._hovered or self._dragging) else "#3E3E50"), 1.0))
        painter.setBrush(cap_grad)
        painter.drawRoundedRect(cap_rect, 3.0, 3.0)

        # Grip grooves on left and right of fader cap
        painter.setPen(QPen(QColor("#14141B"), 1.0))
        painter.drawLine(QPointF(handle_x - 5.0, cap_rect.top() + 3.0), QPointF(handle_x - 5.0, cap_rect.bottom() - 3.0))
        painter.drawLine(QPointF(handle_x + 5.0, cap_rect.top() + 3.0), QPointF(handle_x + 5.0, cap_rect.bottom() - 3.0))

        # Glowing #E5A93C vertical center index line
        painter.setPen(QPen(QColor("#E5A93C"), 2.0))
        painter.drawLine(QPointF(handle_x, cap_rect.top() + 2.0), QPointF(handle_x, cap_rect.bottom() - 2.0))

        painter.end()


class MachinedFaderSlider(QWidget):
    """
    3D Machined Broadcast Fader / Lens Ring Control (Height: 48px).
    - Top row: Parameter Name (#D4D4D8 11px medium) + Value Readout Pill (#101015 recessed box with #E5A93C Consolas 11px bold readout).
    - Bottom row: 11-tick ruler + 3D titanium fader cap.
    - Double-click resets to factory default value.
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

        self.setFixedHeight(48)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(escape_qt_mnemonic(title))
        self.title_label.setStyleSheet("color: #D4D4D8; font-size: 11px; font-weight: 600;")

        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumWidth(54)
        self.value_label.setFixedHeight(19)
        self.value_label.setStyleSheet(
            "background-color: #101015; border: 1px solid #262634; border-radius: 3px; padding: 0px 6px; "
            'color: #E5A93C; font-family: "Consolas", "JetBrains Mono", monospace; font-size: 11px; font-weight: 700;'
        )

        top_row.addWidget(self.title_label)
        top_row.addStretch(1)
        top_row.addWidget(self.value_label)

        self.slider = MachinedGrooveTrack(min_val, max_val, default_val, step=step, bipolar=bipolar, parent=self)
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


# Aliases for Law 2 & backwards compatibility
PrecisionHardwareSlider = MachinedFaderSlider
PrecisionSlider = MachinedFaderSlider


class ToggleSwitch(QAbstractButton):
    """3D Hardware Toggle Row with glowing LED switch."""

    def __init__(self, label_text: str, checked: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._display_text = label_text
        self.setText(escape_qt_mnemonic(label_text))
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        return QSize(280, 28)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        hovered = self.underMouse()
        checked = self.isChecked()

        text_color = QColor("#F4F4F6") if (checked or hovered) else QColor("#B4B4C2")
        painter.setPen(text_color)
        font = self.font()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.DemiBold if checked else QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(
            QRectF(0.0, 0.0, w - 48.0, h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._display_text,
        )

        sw_w, sw_h = 38.0, 20.0
        sw_x = w - sw_w - 2.0
        sw_y = (h - sw_h) * 0.5
        well_rect = QRectF(sw_x, sw_y, sw_w, sw_h)

        # Recessed switch well
        painter.setPen(QPen(QColor("#E5A93C" if checked else "#2E2E3C"), 1.0))
        painter.setBrush(QColor("#1E1910" if checked else "#0B0B10"))
        painter.drawRoundedRect(well_rect, 4.0, 4.0)

        # 3D Machined Switch Actuator Cap
        knob_w, knob_h = 16.0, 14.0
        knob_x = (sw_x + sw_w - knob_w - 3.0) if checked else (sw_x + 3.0)
        knob_y = sw_y + (sw_h - knob_h) * 0.5
        knob_rect = QRectF(knob_x, knob_y, knob_w, knob_h)

        cap_grad = QLinearGradient(0.0, knob_rect.top(), 0.0, knob_rect.bottom())
        if checked:
            cap_grad.setColorAt(0.0, QColor("#F5B945"))
            cap_grad.setColorAt(1.0, QColor("#B47B18"))
        else:
            cap_grad.setColorAt(0.0, QColor("#3A3A4A"))
            cap_grad.setColorAt(1.0, QColor("#1E1E28"))

        painter.setPen(QPen(QColor("#09090D"), 1.0))
        painter.setBrush(cap_grad)
        painter.drawRoundedRect(knob_rect, 2.5, 2.5)
        painter.end()


class SegmentedBar(QWidget):
    """3D Interlocking Mode Selector Bar using TactileHardwareButtons."""

    indexChanged = pyqtSignal(int)

    def __init__(self, labels: List[str], height: int = 38, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.labels = labels
        self._current_index = 0
        self._buttons: List[TactileHardwareButton] = []

        self.setFixedHeight(height)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for idx, text in enumerate(labels):
            btn = TactileHardwareButton(text, led_color="amber", checkable=True, parent=self)
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
            btn.setChecked(i == index)
            btn.update()
        if emit_signal:
            self.indexChanged.emit(index)


class MechanicalShutterButton(QPushButton):
    """
    60x60px 3-Layer 3D Metallic Shutter Release Button:
    - QConicalGradient brushed steel outer ring
    - Recessed dark well
    - Glossy 3D plunger that physically compresses on click
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("3D Mechanical Shutter Release (Capture Lossless Frame)")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() * 0.5, self.height() * 0.5
        center = QPointF(cx, cy)
        hovered = self.underMouse()
        pressed = self.isDown()

        # Layer 1: Brushed steel outer bezel ring (QConicalGradient)
        bezel = QConicalGradient(center, 60.0)
        bezel.setColorAt(0.00, QColor("#525264"))
        bezel.setColorAt(0.25, QColor("#22222C"))
        bezel.setColorAt(0.50, QColor("#68687C"))
        bezel.setColorAt(0.75, QColor("#1A1A22"))
        bezel.setColorAt(1.00, QColor("#525264"))

        painter.setPen(QPen(QColor("#E5A93C" if hovered else "#08080C"), 1.5))
        painter.setBrush(bezel)
        painter.drawEllipse(center, 27.5, 27.5)

        # Layer 2: Recessed dark well
        painter.setPen(QPen(QColor("#09090D"), 1.2))
        painter.setBrush(QColor("#0B0B10"))
        painter.drawEllipse(center, 22.0, 22.0)

        # Layer 3: Glossy 3D metallic plunger
        plunger_r = 17.5 if pressed else 19.5
        plunger_center = QPointF(cx, cy + (1.0 if pressed else 0.0))
        plunger_grad = QRadialGradient(
            QPointF(plunger_center.x() - 5.0, plunger_center.y() - 5.0),
            plunger_r * 1.4,
        )
        if hovered:
            plunger_grad.setColorAt(0.0, QColor("#FFFBEB"))
            plunger_grad.setColorAt(0.6, QColor("#F5B945"))
            plunger_grad.setColorAt(1.0, QColor("#B47B18"))
        else:
            plunger_grad.setColorAt(0.0, QColor("#FFFFFF"))
            plunger_grad.setColorAt(0.7, QColor("#E4E4EC"))
            plunger_grad.setColorAt(1.0, QColor("#9E9EAE"))

        painter.setPen(QPen(QColor("#181820"), 1.0))
        painter.setBrush(plunger_grad)
        painter.drawEllipse(plunger_center, plunger_r, plunger_r)
        painter.end()


ShutterButton = MechanicalShutterButton


class CinemaRecordButton(QPushButton):
    """
    60x60px 3-Layer 3D Metallic Cinema Record Button:
    - QConicalGradient brushed steel outer ring
    - Glowing crimson tally halo when recording
    - 3D crimson plunger morphing to rounded stop square when active
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Start / Stop 1.0x Wall-Clock CFR Video Recording")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() * 0.5, self.height() * 0.5
        center = QPointF(cx, cy)
        recording = self.isChecked()
        hovered = self.underMouse()
        pressed = self.isDown()

        # Glowing crimson tally halo when recording
        if recording:
            halo = QRadialGradient(center, 29.5)
            halo.setColorAt(0.7, QColor(225, 29, 72, 110))
            halo.setColorAt(1.0, QColor(225, 29, 72, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(center, 29.5, 29.5)

        # Layer 1: Brushed steel outer bezel ring
        bezel = QConicalGradient(center, 45.0)
        bezel.setColorAt(0.00, QColor("#4E4E60"))
        bezel.setColorAt(0.25, QColor("#1E1E28"))
        bezel.setColorAt(0.50, QColor("#646478"))
        bezel.setColorAt(0.75, QColor("#181820"))
        bezel.setColorAt(1.00, QColor("#4E4E60"))

        ring_col = QColor("#E11D48") if (recording or hovered) else QColor("#08080C")
        painter.setPen(QPen(ring_col, 1.8 if recording else 1.4))
        painter.setBrush(bezel)
        painter.drawEllipse(center, 27.5, 27.5)

        # Layer 2: Recessed dark well
        painter.setPen(QPen(QColor("#09090D"), 1.2))
        painter.setBrush(QColor("#0B0B10"))
        painter.drawEllipse(center, 22.0, 22.0)

        # Layer 3: Glossy 3D Crimson Plunger
        y_off = 1.0 if pressed else 0.0
        crimson_grad = QRadialGradient(QPointF(cx - 4.0, cy - 4.0 + y_off), 22.0)
        crimson_grad.setColorAt(0.0, QColor("#FB7185"))
        crimson_grad.setColorAt(0.55, QColor("#E11D48"))
        crimson_grad.setColorAt(1.0, QColor("#881337"))

        painter.setPen(QPen(QColor("#181820"), 1.0))
        painter.setBrush(crimson_grad)
        if recording:
            sq = 19.0 if pressed else 21.0
            painter.drawRoundedRect(QRectF(cx - sq * 0.5, cy - sq * 0.5 + y_off, sq, sq), 4.5, 4.5)
        else:
            r = 16.5 if pressed else 18.0
            painter.drawEllipse(QPointF(cx, cy + y_off), r, r)
        painter.end()


RecordButton = CinemaRecordButton


class Lumixa3DLensWidget(QWidget):
    """32x32px 3D Lens Emblem Widget for the Top Left Brand Header."""

    def __init__(self, size: int = 34, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        draw_lumixa_3d_lens(
            painter,
            QRectF(1.0, 1.0, float(self.width() - 2), float(self.height() - 2)),
        )
        painter.end()


ApertureLogoWidget = Lumixa3DLensWidget


class RefreshIconButton(TactileHardwareButton):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", led_color="none", checkable=False, parent=parent)
        self.setFixedSize(32, 32)
        self.setToolTip("Refresh Camera Device List")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        col = QColor("#E5A93C") if self.underMouse() else QColor("#F4F4F6")
        draw_refresh_icon(painter, QRectF(0, 0, float(self.width()), float(self.height())), col)
        painter.end()


class InspectorCard(QFrame):
    """3D Machined Inspector Card container."""

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("InspectorCard")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(13, 11, 13, 13)
        self.main_layout.setSpacing(10)

        header = QLabel(escape_qt_mnemonic(title.upper()))
        header.setObjectName("SectionHeaderLabel")
        self.main_layout.addWidget(header)

    def add_widget(self, widget: QWidget) -> None:
        self.main_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.main_layout.addLayout(layout)
