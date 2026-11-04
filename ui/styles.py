# -*- coding: utf-8 -*-
"""
Minimalist "Camo Studio / Apple Pro Display" Industrial Stylesheet & Vector Icon Painter (`ui/styles.py`).
Clean, breathable dark palette (#09090B canvas, #0D0D10 header, #111115 sidebar, #18181E cards).
"""

import math
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath


OBSIDIAN_LEICA_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #09090B;
    color: #F4F4F6;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 12px;
}

QWidget {
    color: #F4F4F6;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 12px;
}

QFrame#TopHeaderBar {
    background-color: #0D0D10;
    border-bottom: 1px solid #1E1E24;
}

QFrame#BottomCaptureBar {
    background-color: #0D0D10;
    border-top: 1px solid #1E1E24;
}

QFrame#RightStudioSidebar {
    background-color: #111115;
    border-left: 1px solid #1E1E24;
}

QFrame#InspectorCard {
    background-color: #18181E;
    border: 1px solid #24242C;
    border-radius: 8px;
}

QLabel#BrandTitle {
    color: #F4F4F6;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

QLabel#SectionHeaderLabel {
    color: #71717A;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.1px;
}

QPushButton {
    background-color: #1C1C24;
    border: 1px solid #2C2C36;
    border-radius: 6px;
    color: #F4F4F6;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #252530;
    border: 1px solid #3E3E4C;
}

QPushButton:pressed {
    background-color: #2E2E3C;
}

QPushButton:checked {
    background-color: #262118;
    border: 1px solid #E5A93C;
    color: #E5A93C;
    font-weight: 600;
}

QPushButton#VirtualCamButton:checked {
    background-color: #0F2922;
    border: 1px solid #10B981;
    color: #10B981;
    font-weight: 600;
}

QComboBox {
    background-color: #1C1C24;
    border: 1px solid #2C2C36;
    border-radius: 6px;
    color: #F4F4F6;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
}

QComboBox:hover {
    background-color: #252530;
    border: 1px solid #3E3E4C;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #18181E;
    border: 1px solid #2C2C36;
    selection-background-color: #262118;
    selection-color: #E5A93C;
    color: #F4F4F6;
    outline: 0;
}

QLineEdit {
    background-color: #141419;
    border: 1px solid #2C2C36;
    border-radius: 6px;
    color: #F4F4F6;
    padding: 6px 10px;
    font-size: 12px;
}

QLineEdit:focus {
    border: 1px solid #E5A93C;
}

QScrollArea {
    background-color: #111115;
    border: none;
}

QScrollBar:vertical {
    background: #111115;
    width: 5px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2C2C38;
    min-height: 24px;
    border-radius: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #E5A93C;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


def draw_aperture_icon(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Draws a crisp geometric 6-blade lens icon."""
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
    painter.drawArc(arc_rect, 45 * 16, 280 * 16)
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
