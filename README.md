# LUMIXA PRO // C270 CINEMA STUDIO

**Industrial UVC DirectShow Hardware Controller, True 30-FPS Low-Light Unlock Engine, 1D/3D `.CUBE` LUT Color Grading Studio, AI Portrait Segmentation, Wall-Clock 1.0x CFR Synchronized Recorder, and GitHub Auto-Sync Desktop Suite for the Logitech C270 HD Webcam.**

---

## Quick Launch on Windows 10 / 11

Double-click `setup_and_run.bat` (or the automatically created **`Lumixa Pro C270 Studio.lnk`** shortcut on your Windows Desktop). On every launch, it:
1. Pulls the latest commits from GitHub automatically (`git pull --rebase --autostash`).
2. Verifies the `.venv` Python environment and dependencies (`PyQt6`, `opencv-python`, `numpy`, `scipy`, `sounddevice`, `pyvirtualcam`, `imageio-ffmpeg`).
3. Renders the 3D metallic & sapphire-glass lens icon (`lumixa_icon.ico`) and launches **LUMIXA PRO // C270 CINEMA STUDIO**.

---

## Core Engineering Highlights

### 1. Logitech C270 True 30.0 FPS Hardware Unlock & Native Driver Calibration (`core/camera_engine.py`)
- **Mandatory DirectShow MJPG Sequence:** Opens `cv2.VideoCapture(idx, cv2.CAP_DSHOW)`, negotiates `FOURCC = MJPG`, `1280x720`, `30.0 FPS`, re-asserts `MJPG` stream compression, and sets `CAP_PROP_BUFFERSIZE = 1`.
- **Disables the 10.0 FPS Low-Light Compensation Trap:** When **30-FPS Anti-Lag Boost** is active (default ON), sets `CAP_PROP_BACKLIGHT = 0`, `CAP_PROP_AUTO_EXPOSURE = 0.25`, `CAP_PROP_EXPOSURE = -4 EV`, and `CAP_PROP_GAIN = 130`, paired with a zero-latency floating-point shadow-lift curve in software so indoor rooms stay bright at a locked `30.0 FPS`.
- **Exact Native Logitech C270 Hardware Ranges:**
  - `Brightness`: `0..255` (Native Default = `128`)
  - `Contrast`: `0..255` (Native Default = `32`)
  - `Saturation`: `0..255` (Native Default = `32`)
  - `Sharpness`: `0..255` (Native Default = `24`)
  - `Gain`: `0..255` (Native Default = `100`)
  - `Backlight Comp`: `0..2` (Native Default = `0`)
  - `Exposure`: `-11..-2 EV` (Native Default = `-4 EV`)

### 2. Wall-Clock Synchronized 1.0x Constant Frame Rate (CFR) Recorder (`core/recorder_audio.py`)
- Eliminates the "3x fast-forward recording bug" caused by pushing variable-rate webcam frames into a fixed 30 FPS `cv2.VideoWriter`.
- `VideoRecorderThread` runs a 10ms precision wall-clock loop tracking `elapsed_seconds = time.perf_counter() - start_time - total_paused_duration` and pacing `expected_frame_count = int(elapsed_seconds * 30.0)` so a 10.0-second recording always plays back for exactly 10.0 seconds at 1.0x human speed, muxed with 44.1 kHz `.wav` audio into AAC `.mp4` via `ffmpeg`.

### 3. Tactile 3D / 2.5D Cinema Hardware Interface (`ui/`)
- **Programmatic 3D Lens Icon (`ui/styles.py`):** Renders a multi-ring titanium & sapphire/amber glass camera lens emblem (`QConicalGradient` + `QRadialGradient` + 6 aperture blades) and saves `lumixa_icon.ico`.
- **3D Machined Hardware Widgets (`ui/widgets.py`):** `TactileHardwareButton` (`HardwareButton`) with `+1px` mechanical press travel and glowing 3D LED indicator lamps, `MachinedFaderSlider` (`PrecisionHardwareSlider`) with 11 engraved ruler ticks and titanium fader cap, and 60px 3-layer `MechanicalShutterButton` & `CinemaRecordButton`.
- **8 Cinema Film Looks & 12 One-Click Studio Presets (`core/color_lut.py`, `core/preset_manager.py`).**
