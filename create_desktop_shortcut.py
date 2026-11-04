#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — Automatic Windows Desktop Shortcut Generator (`create_desktop_shortcut.py`).
Creates `Lumixa Pro C270 Studio.lnk` on the user's Windows Desktop pointing to `setup_and_run.bat`
and using the programmatically generated 3D camera lens icon `lumixa_icon.ico`.
"""

import os
import subprocess
import sys
from pathlib import Path


def ensure_desktop_shortcut(project_dir: Path | None = None) -> bool:
    """
    Creates a Windows Desktop shortcut named `Lumixa Pro C270 Studio.lnk` using the generated
    3D camera lens icon `lumixa_icon.ico`. Safe no-op on non-Windows platforms.
    """
    if sys.platform != "win32":
        return False

    root = (project_dir or Path(__file__).resolve().parent).resolve()
    bat_path = root / "setup_and_run.bat"
    icon_path = root / "lumixa_icon.ico"

    desktop_dir = Path(os.path.expanduser("~")) / "Desktop"
    if not desktop_dir.exists():
        return False

    shortcut_path = desktop_dir / "Lumixa Pro C270 Studio.lnk"

    ps_script = (
        "$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
        f"$Shortcut.TargetPath = '{bat_path}'; "
        f"$Shortcut.WorkingDirectory = '{root}'; "
        "$Shortcut.Description = 'LUMIXA PRO // C270 CINEMA STUDIO — 30-FPS Optical ISP & Broadcast Recorder'; "
        f"if (Test-Path '{icon_path}') {{ $Shortcut.IconLocation = '{icon_path},0'; }} "
        "$Shortcut.Save()"
    )

    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            creationflags=creationflags,
        )
        return res.returncode == 0 and shortcut_path.exists()
    except Exception:
        return False


if __name__ == "__main__":
    ok = ensure_desktop_shortcut()
    if ok:
        print("[OK] Created Desktop Shortcut: Lumixa Pro C270 Studio.lnk")
    else:
        print("[INFO] Desktop shortcut creation skipped or non-Windows OS.")
