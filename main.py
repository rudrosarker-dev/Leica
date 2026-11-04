#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LEICA // C270 OPTIX STUDIO
Industrial UVC Hardware Controller, Optical ISP Pipeline, 3D LUT Color Grading Engine,
AI Studio Segmentation, and Broadcast Recorder for Logitech C270 HD Webcam.
"""

import sys
import os
import ctypes
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow
from ui.styles import OBSIDIAN_LEICA_STYLESHEET


def apply_windows_dark_titlebar(hwnd: int) -> None:
    """
    Applies Windows 10/11 DWM Dark Mode attribute (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
    and sets caption color to #070709 where supported.
    """
    if sys.platform != "win32":
        return
    try:
        dwmapi = ctypes.windll.dwmapi
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 / Win10 20H1+)
        value = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            int(hwnd),
            20,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        # Fallback attribute 19 for older Windows 10 builds
        dwmapi.DwmSetWindowAttribute(
            int(hwnd),
            19,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        # DWMWA_CAPTION_COLOR = 35 (COLORREF 0x00BBGGRR -> #070709 is 0x00090707)
        caption_color = ctypes.c_int(0x00090707)
        dwmapi.DwmSetWindowAttribute(
            int(hwnd),
            35,
            ctypes.byref(caption_color),
            ctypes.sizeof(caption_color),
        )
    except Exception:
        pass


def global_exception_hook(exc_type, exc_value, exc_traceback) -> None:
    """Global exception dialog ensuring unhandled errors are cleanly reported."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_Details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    sys.stderr.write(f"[CRITICAL EXCEPTION]\n{err_Details}\n")

    app = QApplication.instance()
    if app is not None:
        msg = QMessageBox()
        msg.setWindowTitle("LEICA // C270 OPTIX STUDIO — Runtime Fault")
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("An unexpected runtime exception occurred in the studio pipeline.")
        msg.setInformativeText(str(exc_value))
        msg.setDetailedText(err_Details)
        msg.setStyleSheet(OBSIDIAN_LEICA_STYLESHEET)
        msg.exec()


def ensure_output_directories() -> Path:
    """Ensures ~/Pictures/C270_Optix_Studio exists before launching."""
    pictures_dir = Path.home() / "Pictures" / "C270_Optix_Studio"
    pictures_dir.mkdir(parents=True, exist_ok=True)
    return pictures_dir


def main() -> int:
    sys.excepthook = global_exception_hook

    # High-DPI crispness on fractional scaling displays (125%, 150%, 200%)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("LEICA // C270 OPTIX STUDIO")
    app.setOrganizationName("LeicaOptixBroadcast")
    app.setStyle("Fusion")

    default_font = QFont("Segoe UI", 9)
    default_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(default_font)
    app.setStyleSheet(OBSIDIAN_LEICA_STYLESHEET)

    output_dir = ensure_output_directories()

    window = MainWindow(output_dir=output_dir)
    apply_windows_dark_titlebar(int(window.winId()))
    window.show()
    apply_windows_dark_titlebar(int(window.winId()))

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
