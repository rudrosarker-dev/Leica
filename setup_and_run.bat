@echo off
setlocal EnableDelayedExpansion
title LEICA // C270 OPTIX STUDIO — Automated Setup & Launcher
color 0E

echo ============================================================================
echo   LEICA // C270 OPTIX STUDIO — WINDOWS DESKTOP ENVIRONMENT INITIALIZATION
echo ============================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3.10+ was not found in your Windows PATH.
    echo Please install Python from https://www.python.org/downloads/ and check "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating isolated Python virtual environment (.venv)...
    python -m venv .venv
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Existing virtual environment (.venv) detected.
)

echo [2/4] Upgrading pip, setuptools, and wheel...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel --quiet

echo [3/4] Installing core studio dependencies from requirements.txt...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install core dependencies from requirements.txt.
    pause
    exit /b 1
)

echo [3.5/4] Attempting optional MediaPipe neural segmentation installation...
".venv\Scripts\python.exe" -m pip install mediapipe --quiet 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] MediaPipe wheel not available for this Python version; using built-in OpenCV Haar + Elliptical Radial Optical Segmentation Engine.
) else (
    echo [INFO] MediaPipe neural segmentation engine installed.
)

echo [4/4] Launching LEICA // C270 OPTIX STUDIO...
echo.
".venv\Scripts\python.exe" main.py
endlocal
