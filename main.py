#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO
Native Windows Python (PyQt6 + OpenCV DirectShow) Camera Hardware Controller,
True 30-FPS Low-Light Unlock Engine, 1D/3D .CUBE LUT Color Grading Studio,
AI Portrait Segmentation, Wall-Clock 1.0x CFR Broadcast Recorder, and GitHub Auto-Sync.
"""

import sys
import os
import ctypes
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMessageBox

from create_desktop_shortcut import ensure_desktop_shortcut
from ui.main_window import MainWindow
from ui.styles import OBSIDIAN_LEICA_STYLESHEET, create_lumixa_3d_lens_icon


def apply_windows_dark_titlebar(hwnd: int) -> None:
    """
    Applies Windows 10/11 DWM Dark Mode attribute (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
    and sets caption color to #070709 where supported.
    """
    if sys.platform != "win32":
        return
    try:
        dwmapi = ctypes.windll.dwmapi
        value = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            int(hwnd),
            20,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        dwmapi.DwmSetWindowAttribute(
            int(hwnd),
            19,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
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

    err_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    sys.stderr.write(f"[CRITICAL EXCEPTION]\n{err_details}\n")

    app = QApplication.instance()
    if app is not None:
        msg = QMessageBox()
        msg.setWindowTitle("LUMIXA PRO // C270 CINEMA STUDIO — Runtime Fault")
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("An unexpected runtime exception occurred in the studio pipeline.")
        msg.setInformativeText(str(exc_value))
        msg.setDetailedText(err_details)
        msg.setStyleSheet(OBSIDIAN_LEICA_STYLESHEET)
        msg.exec()


def ensure_output_directories() -> Path:
    """Ensures ~/Pictures/Lumixa_C270_Studio exists before launching."""
    pictures_dir = Path.home() / "Pictures" / "Lumixa_C270_Studio"
    pictures_dir.mkdir(parents=True, exist_ok=True)
    return pictures_dir


def main() -> int:
    sys.excepthook = global_exception_hook

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LumixaPro.C270CinemaStudio.3")
        except Exception:
            pass

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("LUMIXA PRO // C270 CINEMA STUDIO")
    app.setOrganizationName("LumixaCinemaOptics")
    app.setStyle("Fusion")

    # LAW 1: Automatically render 3D lens emblem to 64x64 QIcon, set as app.setWindowIcon(),
    # and save lumixa_icon.ico in root folder for Windows Taskbar and Desktop shortcut.
    root_dir = Path(__file__).resolve().parent
    ico_path = root_dir / "lumixa_icon.ico"
    lens_icon = create_lumixa_3d_lens_icon(size=64, save_ico_path=ico_path)
    app.setWindowIcon(lens_icon)

    # Ensure Windows Desktop shortcut ("Lumixa Pro C270 Studio.lnk") uses lumixa_icon.ico
    ensure_desktop_shortcut(root_dir)

    default_font = QFont("Segoe UI", 9)
    default_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(default_font)
    app.setStyleSheet(OBSIDIAN_LEICA_STYLESHEET)

    output_dir = ensure_output_directories()

    window = MainWindow(output_dir=output_dir)
    window.setWindowIcon(lens_icon)
    apply_windows_dark_titlebar(int(window.winId()))
    window.show()
    apply_windows_dark_titlebar(int(window.winId()))

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
