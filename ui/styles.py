# -*- coding: utf-8 -*-
"""
Obsidian Leica Matte Industrial Design System Stylesheet & Vector Icon Painter (`ui/styles.py`).
Strictly follows the exact color palette with zero emojis and zero generic blue/purple accents.
"""

import math
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath


# Exact Hex Palette Constants
HEX_VOID_BG = "#070709"
HEX_BAR_BG = "#0A0A0D"
HEX_DOCK_BG = "#0E0E12"
HEX_CARD_BG = "#15151B"
HEX_CARD_BORDER = "#22222B"
HEX_CTRL_IDLE = "#1C1C24"
HEX_CTRL_BORDER = "#2C2C38"
HEX_CTRL_HOVER = "#252530"
HEX_CTRL_HOVER_BORDER = "#3E3E4E"
HEX_CTRL_ACTIVE = "#2E2E3C"
HEX_ACCENT_AMBER = "#E5A93C"
HEX_TALLY_RED = "#E11D48"
HEX_LIVE_EMERALD = "#10B981"
HEX_WARN_AMBER = "#F59E0B"
HEX_TEXT_PRIMARY = "#F4F4F6"
HEX_TEXT_SECONDARY = "#9CA3AF"
HEX_TEXT_HEADER = "#71717A"


OBSIDIAN_LEICA_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #070709;
    color: #F4F4F6;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 12px;
}

QWidget {
    color: #F4F4F6;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 12px;
}

QFrame#TopTelemetryBar {
    background-color: #0A0A0D;
    border-bottom: 1px solid #22222B;
}

QFrame#BottomTransportDeck {
    background-color: #0A0A0D;
    border-top: 1px solid #22222B;
}

QFrame#LeftInspectorDock {
    background-color: #0E0E12;
    border-right: 1px solid #22222B;
}

QFrame#RightInspectorDock {
    background-color: #0E0E12;
    border-left: 1px solid #22222B;
}

QFrame#InspectorCard {
    background-color: #15151B;
    border: 1px solid #22222B;
    border-radius: 6px;
}

QLabel#BrandTitle {
    color: #F4F4F6;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.5px;
}

QLabel#SectionHeaderLabel {
    color: #71717A;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
}

QLabel#TelemetryBadge {
    background-color: #14141A;
    border: 1px solid #262632;
    border-radius: 4px;
    padding: 3px 8px;
    color: #E5A93C;
    font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 600;
}

QLabel#MasterTimecode {
    color: #F4F4F6;
    font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 15px;
    font-weight: 700;
}

QPushButton {
    background-color: #1C1C24;
    border: 1px solid #2C2C38;
    border-radius: 4px;
    color: #F4F4F6;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #252530;
    border: 1px solid #3E3E4E;
}

QPushButton:pressed {
    background-color: #2E2E3C;
}

QPushButton:checked {
    background-color: #262118;
    border: 1px solid #E5A93C;
    color: #E5A93C;
}

QPushButton#VirtualCamButton:checked {
    background-color: #0F2922;
    border: 1px solid #10B981;
    color: #10B981;
}

QComboBox {
    background-color: #1C1C24;
    border: 1px solid #2C2C38;
    border-radius: 4px;
    color: #F4F4F6;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 500;
}

QComboBox:hover {
    background-color: #252530;
    border: 1px solid #3E3E4E;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #15151B;
    border: 1px solid #2C2C38;
    selection-background-color: #262118;
    selection-color: #E5A93C;
    color: #F4F4F6;
    outline: 0;
}

QLineEdit {
    background-color: #1C1C24;
    border: 1px solid #2C2C38;
    border-radius: 4px;
    color: #F4F4F6;
    padding: 5px 8px;
    font-size: 11px;
    selection-background-color: #E5A93C;
    selection-color: #070709;
}

QLineEdit:focus {
    border: 1px solid #E5A93C;
}

QScrollArea {
    background-color: #0E0E12;
    border: none;
}

QScrollBar:vertical {
    background: #0E0E12;
    width: 5px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2E2E3A;
    min-height: 24px;
    border-radius: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #E5A93C;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QToolTip {
    background-color: #15151B;
    color: #F4F4F6;
    border: 1px solid #E5A93C;
    padding: 4px 6px;
    font-size: 11px;
}
"""


def draw_aperture_icon(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """
    Draws a precision geometric Leica 6-blade lens aperture icon inside `rect`
    using QPainterPath and trigonometric blade lines.
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    cx = rect.center().x()
    cy = rect.center().y()
    r_outer = min(rect.width(), rect.height()) * 0.44
    r_inner = r_outer * 0.42

    pen = QPen(color, 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    painter.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

    # 6 angled iris blades tangent to inner hexagon
    for i in range(6):
        angle_deg = i * 60.0 + 15.0
        rad1 = math.radians(angle_deg)
        rad2 = math.radians(angle_deg + 55.0)
        x1 = cx + r_inner * math.cos(rad1)
        y1 = cy + r_inner * math.sin(rad1)
        x2 = cx + (r_outer * 0.94) * math.cos(rad2)
        y2 = cy + (r_outer * 0.94) * math.sin(rad2)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    painter.restore()


def draw_refresh_icon(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Draws a crisp circular arrow arc icon for Refresh Devices."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    cx = rect.center().x()
    cy = rect.center().y()
    radius = min(rect.width(), rect.height()) * 0.28

    pen = QPen(color, 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    arc_rect = QRectF(cx - radius, cy - radius, radius * 2.0, radius * 2.0)
    # Draw 280-degree arc (in 1/16th degrees)
    painter.drawArc(arc_rect, 45 * 16, 280 * 16)

    # Draw arrowhead at ~45 degrees
    tip_angle = math.radians(45.0)
    tx = cx + radius * math.cos(tip_angle)
    ty = cy - radius * math.sin(tip_angle)

    path = QPainterPath()
    path.moveTo(tx, ty)
    path.lineTo(tx - 4.2, ty - 1.0)
    path.moveTo(tx, ty)
    path.lineTo(tx - 0.8, ty + 4.2)
    painter.drawPath(path)

    painter.restore()
