@echo off
setlocal EnableDelayedExpansion
title LUMIXA PRO // C270 CINEMA STUDIO — Standalone EXE Builder (PyInstaller)
color 0E

echo ============================================================================
echo   LUMIXA PRO // C270 CINEMA STUDIO — STANDALONE WINDOWS .EXE COMPILER
echo ============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment and installing dependencies...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    ".venv\Scripts\python.exe" -m pip install mediapipe 2>nul
)

echo [2/3] Installing PyInstaller...
".venv\Scripts\python.exe" -m pip install pyinstaller

echo [3/3] Building standalone Lumixa_Pro_C270_Studio.exe...
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --onefile ^
    --name "Lumixa_Pro_C270_Studio" ^
    --hidden-import "PyQt6" ^
    --hidden-import "cv2" ^
    --hidden-import "numpy" ^
    --hidden-import "scipy" ^
    --hidden-import "sounddevice" ^
    --hidden-import "pyvirtualcam" ^
    --hidden-import "imageio_ffmpeg" ^
    main.py

echo.
if exist "dist\Lumixa_Pro_C270_Studio.exe" (
    echo [SUCCESS] Standalone executable built at: dist\Lumixa_Pro_C270_Studio.exe
) else (
    echo [ERROR] PyInstaller build did not produce dist\Lumixa_Pro_C270_Studio.exe
)
pause
endlocal
