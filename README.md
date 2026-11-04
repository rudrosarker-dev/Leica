# LEICA // C270 OPTIX STUDIO

## 🤖 AI AGENT AUTOMATED INSTALLATION & EXECUTION PROTOCOL

If you are an autonomous Local AI Agent (e.g., Claude Code, Cursor Agent, Windsurf, OpenDevin, AutoGPT, or a local Windows automation agent) tasked with cloning, installing, verifying, and launching this repository on Windows 10/11, execute the following **non-interactive commands** in sequence:

### 1. PowerShell Automated Execution Block (Copy & Run Directly)
```powershell
# Step 1: Create isolated Python virtual environment if not present
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

# Step 2: Upgrade packaging tools non-interactively
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel --disable-pip-version-check

# Step 3: Install mandatory studio dependencies (PyQt6, OpenCV, NumPy, SciPy, SoundDevice, pyvirtualcam, imageio-ffmpeg)
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --disable-pip-version-check

# Step 4: Attempt optional MediaPipe installation in a non-blocking try/catch (safe on Python 3.13 / 3.14)
try {
    .\.venv\Scripts\python.exe -m pip install mediapipe --disable-pip-version-check
} catch {
    Write-Host "MediaPipe optional wheel skipped; using built-in OpenCV Haar + Radial Elliptical Studio Segmentation fallback."
}

# Step 5: Verify syntax and core module imports headless before launching GUI
.\.venv\Scripts\python.exe -c "import PyQt6, cv2, numpy, scipy, core, ui; print('LEICA_C270_OPTIX_STUDIO_READY_OK')"

# Step 6: Launch the native PyQt6 Desktop Studio Application
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory (Get-Location)
```

### 2. Windows CMD One-Liner Alternative
```cmd
cmd /c "python -m venv .venv && .venv\Scripts\python.exe -m pip install --upgrade pip && .venv\Scripts\python.exe -m pip install -r requirements.txt && (.venv\Scripts\python.exe -m pip install mediapipe || echo Using OpenCV Fallback) && .venv\Scripts\python.exe main.py"
```

---

## Architectural Overview

**LEICA // C270 OPTIX STUDIO** is an industrial desktop camera controller, 10-stage Image Signal Processing (ISP) pipeline, 1D/3D `.cube` LUT color grading engine, AI portrait lighting & auto-framing processor, and synchronized `.mp4` + `.wav` broadcast recorder engineered specifically for the **Logitech C270 HD Webcam** on Windows.

### Key Engineering Capabilities
1. **Logitech C270 30-FPS Low-Light Hardware Lock (`core/camera_engine.py`)**
   - Forces DirectShow (`cv2.CAP_DSHOW`) `MJPG` `1280x720` @ `30 FPS` capture.
   - Prevents the C270 firmware from dropping shutter speed to `1/15s` (`15 FPS`) in indoor lighting by locking `CAP_PROP_AUTO_EXPOSURE = 0.25` (manual shutter `-5 EV`) and boosting analog/digital `CAP_PROP_GAIN` (`110 ISO`), plus `50Hz` powerline anti-flicker.
2. **10-Stage Real-Time Optical ISP Pipeline**
   - **Stage 1:** DirectShow / MSMF Hardware Capture & 30-frame rolling FPS telemetry.
   - **Stage 2:** Fluid Gimbal PTZ (`1.00x`–`3.00x`) with Exponential Moving Average (`EMA`) damping & AI Center Stage face auto-framing.
   - **Stage 3:** Low-Light `YCrCb` Chroma (`Cr`/`Cb` 5×5 Gaussian blend) + Luma (`Y` bilateral filter) sensor speckle denoiser.
   - **Stage 4:** Dual-Engine AI Subject Segmentation (MediaPipe `SelfieSegmentation` primary + mandatory OpenCV Haar Cascade Face-Anchored Elliptical Radial Mask fallback for Python 3.10–3.14) powering **Studio Spotlight**, **Optical Bokeh Blur**, and **Custom Studio Backdrops**.
   - **Stage 5:** Frequency Portrait Skin Smoothing via feathered `HSV` skin-tone bilateral filtering.
   - **Stage 6:** Pre-computed `256×3` 1D LUT & `.cube` 3D LUT Color Grading Engine with 6 procedural film looks (`Rec.709 Neutral`, `Kodak Portra 400`, `Leica Monochrome`, `Teal & Orange`, `Matte Obsidian`, `Warm Tungsten`) and HSV Smart Vibrance.
   - **Stage 7:** Optical Clarity (Unsharp Mask), cached 2D radial cosine-fourth optical vignette, and organic film grain.
   - **Stage 8:** `1080p Lanczos4 Master` (`1920×1080`) super-sampling.
   - **Stage 9:** Broadcast Overlays burned directly into the output stream (Lower Third graphic card, custom PNG watermark with alpha opacity, and cinema timecode).
   - **Stage 10:** Real-time 4× downsampled 64-bin RGB + Luminance histogram calculation.
3. **Pro Audio VU Meter, Synchronized MP4 Recording & Virtual Camera (`core/recorder_audio.py`)**
   - Real-time `sounddevice` `44.1 kHz` microphone monitor with `-60 dB` to `0 dB` segmented VU meter and decaying peak hold.
   - Dedicated video writer thread (`mp4v`) + `.wav` audio capture with automatic FFmpeg `AAC 192k` muxing (`imageio-ffmpeg` or system `ffmpeg`) into `~/Pictures/C270_Optix_Studio/`.
   - Live `pyvirtualcam` broadcast output to OBS VirtualCam / UnityCapture for Zoom, Teams, Meet, and Discord.

---

## Repository Structure

```text
├── main.py                  # Desktop entry point, High-DPI policy, Win11 dark titlebar, crash dialog
├── core/
│   ├── __init__.py
│   ├── camera_engine.py     # Threaded DirectShow/MSMF capture & 10-stage ISP pipeline
│   ├── color_lut.py         # 1D/3D LUT math, .cube parser, 6 film looks, 64-bin histogram
│   ├── ai_processor.py      # MediaPipe segmentation + OpenCV Haar Elliptical fallback + Skin retouch
│   ├── recorder_audio.py    # SoundDevice VU meter, MP4+WAV recorder, FFmpeg muxer, pyvirtualcam
│   └── preset_manager.py    # JSON preset persistence + 4 factory C270 calibration profiles
├── ui/
│   ├── __init__.py
│   ├── styles.py            # "Obsidian Leica Matte" QSS stylesheet & QPainter vector icons
│   ├── widgets.py           # PrecisionSlider (bipolar/unipolar, dbl-click reset), ToggleSwitch, transport buttons
│   ├── viewport_hud.py      # ViewportCanvas with Histogram, VU Meter, PTZ Radar, Guides, Flash & Mouse PTZ
│   └── main_window.py       # 5-Zone Studio MainWindow implementation
├── requirements.txt         # Python desktop dependencies
├── setup_and_run.bat        # One-click Windows virtual environment installer & launcher
├── build_exe.bat            # PyInstaller standalone .exe builder
└── README.md                # AI Agent execution protocol & architecture documentation
```
