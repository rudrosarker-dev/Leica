# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — 3D/2.5D Skeuomorphic Hardware UI Stylesheet & 3D Lens Emblem Generator (`ui/styles.py`).

LAW 1 & SECTION 3.1 COMPLIANCE:
- Official Brand Name: `LUMIXA PRO // C270 CINEMA STUDIO`
- Programmatic 3D Lens Icon & Logo (`create_lumixa_3d_lens_icon(size=64)`):
  Uses `QPainter` with Antialiasing to draw:
  1. Outer machined titanium barrel ring (`QConicalGradient` metallic silver/charcoal `#4A4A58` to `#181820`).
  2. Knurled grip ridges around the circumference.
  3. Deep recessed matte black lens barrel (`#08080C`).
  4. Multi-coated optical sapphire/amber glass element (`QRadialGradient` with `#E5A93C` warm tungsten reflex,
     `#0EA5E9` cyan anti-reflective coating glint, and `#050508` core).
  5. 6 geometric iris aperture blades and a crisp specular white reflection arc.
  Automatically renders and saves `lumixa_icon.ico` in the root folder for Windows Taskbar and Desktop shortcut.
"""

import math
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPainterPath,
    QPixmap,
    QIcon,
    QRadialGradient,
    QConicalGradient,
    QLinearGradient,
)


OBSIDIAN_LEICA_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #08080B;
    color: #F4F4F6;
    font-family: "Segoe UI", "Plus Jakarta Sans", sans-serif;
    font-size: 12px;
}

QWidget {
    color: #F4F4F6;
    font-family: "Segoe UI", "Plus Jakarta Sans", sans-serif;
    font-size: 12px;
}

QFrame#TopHeaderBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #16161E, stop:1 #0B0B10);
    border-bottom: 1px solid #262632;
}

QFrame#RecessedLCDPanel {
    background-color: #08080B;
    border: 1px solid #262632;
    border-radius: 5px;
}

QFrame#BottomCaptureBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #14141C, stop:1 #0A0A0E);
    border-top: 1px solid #262632;
}

QFrame#RightStudioSidebar {
    background-color: #0E0E13;
    border-left: 1px solid #242430;
}

QFrame#InspectorCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #171720, stop:1 #111118);
    border-top: 1px solid #2E2E3C;
    border-left: 1px solid #242430;
    border-right: 1px solid #242430;
    border-bottom: 1px solid #09090D;
    border-radius: 6px;
}

QLabel#BrandTitle {
    color: #F4F4F6;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1.4px;
}

QLabel#BrandSubtitle {
    color: #E5A93C;
    font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.2px;
}

QLabel#SectionHeaderLabel {
    color: #A1A1B0;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
}

QComboBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #262632, stop:1 #14141B);
    border-top: 1px solid #3E3E50;
    border-left: 1px solid #2C2C3A;
    border-right: 1px solid #2C2C3A;
    border-bottom: 1px solid #08080B;
    border-radius: 5px;
    color: #F4F4F6;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}

QComboBox:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2E2E3E, stop:1 #1A1A24);
    border-top: 1px solid #E5A93C;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #14141C;
    border: 1px solid #3E3E50;
    selection-background-color: #262118;
    selection-color: #E5A93C;
    color: #F4F4F6;
    outline: 0;
}

QLineEdit {
    background-color: #0B0B10;
    border-top: 1px solid #060609;
    border-left: 1px solid #1C1C26;
    border-right: 1px solid #1C1C26;
    border-bottom: 1px solid #2E2E3C;
    border-radius: 4px;
    color: #F4F4F6;
    padding: 5px 10px;
    font-size: 11px;
}

QLineEdit:focus {
    border: 1px solid #E5A93C;
}

QScrollArea {
    background-color: #0E0E13;
    border: none;
}

QScrollBar:vertical {
    background: #0B0B0F;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2E2E3C;
    min-height: 28px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #E5A93C;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


def draw_lumixa_3d_lens(painter: QPainter, rect: QRectF) -> None:
    """
    Draws the multi-ring 3D metallic & sapphire-glass camera lens emblem using QPainter:
    1. Outer machined titanium barrel ring (QConicalGradient #4A4A58 to #181820)
    2. Knurled grip ridges around the circumference
    3. Deep recessed matte black lens barrel (#08080C)
    4. Multi-coated optical sapphire/amber glass element (QRadialGradient with #E5A93C warm tungsten reflex,
       #0EA5E9 cyan anti-reflective coating glint, and #050508 core)
    5. 6 geometric iris aperture blades and crisp specular white reflection arc
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    cx = rect.center().x()
    cy = rect.center().y()
    center = QPointF(cx, cy)
    max_r = min(rect.width(), rect.height()) * 0.47

    # 1. Outer Machined Titanium Barrel Ring (QConicalGradient)
    conical = QConicalGradient(center, 45.0)
    conical.setColorAt(0.00, QColor("#4A4A58"))
    conical.setColorAt(0.25, QColor("#181820"))
    conical.setColorAt(0.50, QColor("#565666"))
    conical.setColorAt(0.75, QColor("#14141B"))
    conical.setColorAt(1.00, QColor("#4A4A58"))

    painter.setPen(QPen(QColor("#060609"), max(1.0, max_r * 0.04)))
    painter.setBrush(conical)
    painter.drawEllipse(center, max_r, max_r)

    # 2. Knurled Grip Ridges around the circumference (24 precision ticks)
    ridge_pen = QPen(QColor(255, 255, 255, 55), max(1.0, max_r * 0.035))
    painter.setPen(ridge_pen)
    for i in range(24):
        ang = math.radians(i * 15.0)
        r1 = max_r * 0.88
        r2 = max_r * 0.97
        painter.drawLine(
            QPointF(cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)),
            QPointF(cx + r2 * math.cos(ang), cy + r2 * math.sin(ang)),
        )

    # Gold/Amber Leica/CineAlta Anodized Index Ring
    ring_r = max_r * 0.82
    painter.setPen(QPen(QColor("#E5A93C"), max(1.1, max_r * 0.045)))
    painter.setBrush(QColor("#08080C"))
    painter.drawEllipse(center, ring_r, ring_r)

    # 3. Deep Recessed Matte Black Lens Barrel (#08080C)
    barrel_r = max_r * 0.74
    barrel_grad = QLinearGradient(cx, cy - barrel_r, cx, cy + barrel_r)
    barrel_grad.setColorAt(0.0, QColor("#050508"))
    barrel_grad.setColorAt(1.0, QColor("#181822"))
    painter.setPen(QPen(QColor("#262634"), 1.0))
    painter.setBrush(barrel_grad)
    painter.drawEllipse(center, barrel_r, barrel_r)

    # 4. Multi-Coated Optical Sapphire/Amber Glass Element (QRadialGradient)
    glass_r = max_r * 0.62
    glass_grad = QRadialGradient(
        QPointF(cx - glass_r * 0.25, cy - glass_r * 0.25),
        glass_r * 1.35,
    )
    glass_grad.setColorAt(0.00, QColor("#0EA5E9"))   # Sapphire cyan AR coating glint
    glass_grad.setColorAt(0.32, QColor("#0D2538"))   # Deep optical sapphire
    glass_grad.setColorAt(0.68, QColor("#050508"))   # Dark optical core
    glass_grad.setColorAt(0.90, QColor("#E5A93C"))   # Warm tungsten amber reflex rim
    glass_grad.setColorAt(1.00, QColor("#050508"))

    painter.setPen(QPen(QColor("#1E293B"), 1.0))
    painter.setBrush(glass_grad)
    painter.drawEllipse(center, glass_r, glass_r)

    # 5. 6 Geometric Iris Aperture Blades
    r_inner = glass_r * 0.36
    r_blade_outer = glass_r * 0.88
    blade_pen = QPen(QColor(229, 169, 60, 165), max(1.0, max_r * 0.04))
    blade_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(blade_pen)
    for i in range(6):
        angle_deg = i * 60.0 + 18.0
        rad1 = math.radians(angle_deg)
        rad2 = math.radians(angle_deg + 54.0)
        x1 = cx + r_inner * math.cos(rad1)
        y1 = cy + r_inner * math.sin(rad1)
        x2 = cx + r_blade_outer * math.cos(rad2)
        y2 = cy + r_blade_outer * math.sin(rad2)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    # Crisp Specular White Reflection Arc on Upper-Left Glass Element
    spec_r = glass_r * 0.76
    spec_rect = QRectF(cx - spec_r, cy - spec_r, spec_r * 2.0, spec_r * 2.0)
    spec_pen = QPen(QColor(255, 255, 255, 180), max(1.2, max_r * 0.055))
    spec_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(spec_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(spec_rect, 115 * 16, 48 * 16)

    painter.restore()


def create_lumixa_3d_lens_pixmap(size: int = 64) -> QPixmap:
    """Renders the 3D Lens Emblem to a transparent QPixmap of the requested size."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    draw_lumixa_3d_lens(painter, QRectF(1.0, 1.0, float(size - 2), float(size - 2)))
    painter.end()
    return pixmap


def create_lumixa_3d_lens_icon(size: int = 64, save_ico_path: Optional[Path] = None) -> QIcon:
    """
    Generates the multi-resolution QIcon for `app.setWindowIcon()` and saves `lumixa_icon.ico`
    in the root folder so the Windows Taskbar and Desktop shortcut display the 3D camera lens icon.
    """
    icon = QIcon()
    for sz in (16, 24, 32, 48, 64, 128):
        px = create_lumixa_3d_lens_pixmap(sz)
        icon.addPixmap(px)

    target_ico = save_ico_path or (Path(__file__).resolve().parent.parent / "lumixa_icon.ico")
    try:
        px64 = create_lumixa_3d_lens_pixmap(size)
        px64.save(str(target_ico), "ICO")
    except Exception:
        pass
    return icon


def draw_aperture_icon(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Legacy wrapper that delegates to the full 3D Lumixa Lens Emblem renderer."""
    draw_lumixa_3d_lens(painter, rect)


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
