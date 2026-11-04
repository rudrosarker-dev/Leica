@echo off
setlocal EnableDelayedExpansion
title LUMIXA PRO // C270 CINEMA STUDIO — Automated GitHub Sync & Launcher
color 0E

echo ============================================================================
echo   LUMIXA PRO // C270 CINEMA STUDIO — WINDOWS DESKTOP LAUNCHER ^& CLOUD SYNC
echo ============================================================================
echo.

REM LAW 5: Automatically pull latest updates from GitHub on every launch (ignoring errors if offline)
where git >nul 2>nul
if %ERRORLEVEL% equ 0 (
    if exist ".git" (
        echo [SYNC] Checking GitHub repository for latest LUMIXA PRO updates...
        git fetch --all --quiet 2>nul
        git pull --rebase --autostash 2>nul
    )
)

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
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install core dependencies from requirements.txt.
    pause
    exit /b 1
)

echo [3.5/4] Ensuring Windows Desktop Shortcut (Lumixa Pro C270 Studio.lnk)...
".venv\Scripts\python.exe" create_desktop_shortcut.py 2>nul

echo [4/4] Launching LUMIXA PRO // C270 CINEMA STUDIO...
echo.
".venv\Scripts\python.exe" main.py
endlocal
