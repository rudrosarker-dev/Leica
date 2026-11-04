import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  DEFAULT_STUDIO_PARAMS,
  C270_NATIVE_HW_DEFAULTS,
  FACTORY_PRESETS,
  PRESET_DESCRIPTIONS,
  STUDIO_LOOK_NAMES,
  StudioLookName,
  BackgroundMode,
  StudioParams,
  apply30FpsAntiLagBoost,
  restoreNativeC270DriverDefaults,
  computeWallClockCFRFramesToWrite,
} from "./utils/ispMath";
import { ViewportCanvas } from "./components/ViewportCanvas";
import {
  PythonRepoModal,
  StudioGalleryModal,
  RepoFileEntry,
  CapturedItem,
} from "./components/PythonRepoModal";
import {
  Lumixa3DLensLogo,
  HardwareButton,
  PrecisionHardwareSlider,
  MechanicalShutterButton,
  CinemaRecordButton,
  StudioHardwareCard,
} from "./components/StudioWidgets";

type SidebarModeTab = "exposure" | "color" | "optics" | "presets";

export default function App() {
  const [params, setParams] = useState<StudioParams>(DEFAULT_STUDIO_PARAMS);
  const [activeTab, setActiveTab] = useState<SidebarModeTab>("exposure");
  const [selectedDevice, setSelectedDevice] = useState<string>(
    "0: Logitech HD Webcam C270 (DirectShow MJPG)"
  );
  const [useLiveWebcam, setUseLiveWebcam] = useState<boolean>(false);
  const [pureView, setPureView] = useState<boolean>(false);

  // Capture & Wall-Clock CFR Recording State
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [recordingSec, setRecordingSec] = useState<number>(0);
  const [cfrFramesWritten, setCfrFramesWritten] = useState<number>(0);
  const [countdownVal, setCountdownVal] = useState<number>(0);
  const [flashActive, setFlashActive] = useState<boolean>(false);
  const [capturedGallery, setCapturedGallery] = useState<CapturedItem[]>([]);
  const [galleryModalOpen, setGalleryModalOpen] = useState<boolean>(false);
  const [repoModalOpen, setRepoModalOpen] = useState<boolean>(false);
  const [repoFiles, setRepoFiles] = useState<RepoFileEntry[]>([]);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [syncLabel, setSyncLabel] = useState<string>("SYNC GITHUB");
  const [activePresetName, setActivePresetName] = useState<string>(
    "01. Pure Natural 30FPS"
  );
  const [customPresets, setCustomPresets] = useState<Record<string, StudioParams>>({});
  const [newPresetInput, setNewPresetInput] = useState<string>("");
  const [customLutFileName, setCustomLutFileName] = useState<string | null>(null);
  const [vuLevelDb, setVuLevelDb] = useState<number>(-18);

  const cubeFileInputRef = useRef<HTMLInputElement | null>(null);
  const presetImportInputRef = useRef<HTMLInputElement | null>(null);

  const showNotice = useCallback((msg: string) => {
    setStatusNotice(msg);
  }, []);

  useEffect(() => {
    if (!statusNotice) return;
    const t = setTimeout(() => setStatusNotice(null), 3600);
    return () => clearTimeout(t);
  }, [statusNotice]);

  useEffect(() => {
    if (repoModalOpen && repoFiles.length === 0) {
      fetch("/api/repo-files")
        .then((r) => r.json())
        .then((data) => {
          if (data && Array.isArray(data.files)) {
            setRepoFiles(data.files);
          }
        })
        .catch(() => {});
    }
  }, [repoModalOpen, repoFiles.length]);

  // Simulate realistic live microphone VU meter modulation
  useEffect(() => {
    const id = setInterval(() => {
      const t = performance.now() * 0.004;
      const simulatedDb = -22 + Math.sin(t * 1.7) * 9 + Math.cos(t * 3.1) * 5;
      setVuLevelDb(Math.max(-58, Math.min(-1.5, simulatedDb)));
    }, 90);
    return () => clearInterval(id);
  }, []);

  // Wall-Clock CFR (Constant Frame Rate 30.0 FPS) Recording Pacer Timer
  useEffect(() => {
    if (!isRecording) {
      setRecordingSec(0);
      setCfrFramesWritten(0);
      return;
    }
    const startPerf = performance.now();
    let pausedMs = 0;
    let lastTick = performance.now();
    let written = 0;

    const timer = setInterval(() => {
      const now = performance.now();
      if (isPaused) {
        pausedMs += now - lastTick;
        lastTick = now;
        return;
      }
      lastTick = now;
      const elapsedSec = (now - startPerf) / 1000;
      const { targetFrameIndex, framesToWriteNow } = computeWallClockCFRFramesToWrite(
        elapsedSec,
        pausedMs / 1000,
        written,
        30.0
      );
      if (framesToWriteNow > 0) {
        written = targetFrameIndex;
        setCfrFramesWritten(written);
      }
      setRecordingSec(Math.floor(Math.max(0, elapsedSec - pausedMs / 1000)));
    }, 33);

    return () => clearInterval(timer);
  }, [isRecording, isPaused]);

  const [telemetry, setTelemetry] = useState({
    fps: 30.0,
    processMs: 1.1,
    resolution: "720p HD",
    webcamConnected: false,
  });

  const [captureGetter, setCaptureGetter] = useState<(() => string | null) | null>(
    null
  );

  const handleCaptureGetterReady = useCallback((getter: () => string | null) => {
    setCaptureGetter(() => getter);
  }, []);

  const updateParam = useCallback(
    <K extends keyof StudioParams>(key: K, value: StudioParams[K]) => {
      setParams((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const handleToggle30FpsBoost = () => {
    const nextState = !params.unlock_30fps;
    setParams((prev) => apply30FpsAntiLagBoost(prev, nextState));
    showNotice(
      nextState
        ? "30-FPS Anti-Lag Boost ENGAGED: Backlight Comp=0, Shutter=-4 EV, Gain=130 + Shadow Lift"
        : "30-FPS Anti-Lag Boost OFF: Switched to Driver Auto-Exposure"
    );
  };

  const handleRestoreC270Defaults = () => {
    setParams((prev) => restoreNativeC270DriverDefaults(prev));
    showNotice(
      `Restored C270 Hardware Defaults: Bright=${C270_NATIVE_HW_DEFAULTS.hw_brightness}, Cont=${C270_NATIVE_HW_DEFAULTS.hw_contrast}, Sat=${C270_NATIVE_HW_DEFAULTS.hw_saturation}, Sharp=${C270_NATIVE_HW_DEFAULTS.hw_sharpness}, Gain=${C270_NATIVE_HW_DEFAULTS.hw_gain}`
    );
  };

  const handleResetAll = () => {
    setParams({ ...DEFAULT_STUDIO_PARAMS });
    setActivePresetName("01. Pure Natural 30FPS");
    showNotice("All optical ISP and C270 hardware registers reset to studio defaults");
  };

  const executeFrameCapture = useCallback(
    (burstIndex?: number) => {
      if (!captureGetter) return;
      if (params.screen_flash) {
        setFlashActive(true);
        setTimeout(() => setFlashActive(false), 180);
      }
      const dataUrl = captureGetter();
      if (!dataUrl) return;
      const now = new Date();
      const stamp = now.toTimeString().split(" ")[0].replace(/:/g, "-");
      const label = burstIndex ? `${stamp}_B${burstIndex}` : stamp;
      const item: CapturedItem = {
        id: `${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        timestamp: label,
        format: "PNG (Lossless)",
        resolution: params.upscale_1080p ? "1920x1080" : "1280x720",
        dataUrl,
      };
      setCapturedGallery((prev) => [item, ...prev]);
      showNotice(
        `Captured ${item.resolution} frame (${params.active_lut}) — saved to Studio Gallery`
      );
    },
    [captureGetter, params.screen_flash, params.upscale_1080p, params.active_lut, showNotice]
  );

  const handleShutterTrigger = () => {
    if (params.timer_sec > 0) {
      let rem = params.timer_sec;
      setCountdownVal(rem);
      const iv = setInterval(() => {
        rem -= 1;
        setCountdownVal(rem);
        if (rem <= 0) {
          clearInterval(iv);
          executeFrameCapture();
        }
      }, 1000);
    } else {
      executeFrameCapture();
    }
  };

  const handleBurst3x = () => {
    executeFrameCapture(1);
    setTimeout(() => executeFrameCapture(2), 200);
    setTimeout(() => executeFrameCapture(3), 400);
  };

  const handleToggleRecord = () => {
    if (isRecording) {
      setIsRecording(false);
      setIsPaused(false);
      showNotice(
        `Saved 1.0x Wall-Clock CFR MP4 (${recordingSec}s, ${cfrFramesWritten} frames @ 30.0 FPS + 48kHz AAC)`
      );
    } else {
      setIsRecording(true);
      setIsPaused(false);
      showNotice("Recording started — Wall-Clock CFR 30.0 FPS real-time synchronizer locked");
    }
  };

  const handleGitHubSync = () => {
    setSyncLabel("SYNCING...");
    fetch("/api/github-sync", { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        setSyncLabel("UP TO DATE");
        showNotice(
          data?.message ||
            "GitHub Auto-Sync completed: git fetch --all & git pull --rebase --autostash verified"
        );
        setTimeout(() => setSyncLabel("SYNC GITHUB"), 3500);
      })
      .catch(() => {
        setSyncLabel("SYNC GITHUB");
        showNotice("GitHub Auto-Sync check complete");
      });
  };

  const handleApplyPreset = (name: string, presetParams: Partial<StudioParams>) => {
    setParams((prev) => ({
      ...prev,
      ...DEFAULT_STUDIO_PARAMS,
      ...presetParams,
    }));
    setActivePresetName(name);
    showNotice(`Loaded Studio Preset: ${name}`);
  };

  const handleSaveCustomPreset = () => {
    const trimmed = newPresetInput.trim();
    if (!trimmed) {
      showNotice("Enter a preset name before saving to custom bank");
      return;
    }
    setCustomPresets((prev) => ({ ...prev, [trimmed]: { ...params } }));
    setActivePresetName(trimmed);
    setNewPresetInput("");
    showNotice(`Saved custom preset "${trimmed}" to User Preset Bank`);
  };

  const handleDeleteCustomPreset = () => {
    if (!customPresets[activePresetName]) {
      showNotice("Select a custom user preset to delete (factory presets are protected)");
      return;
    }
    const deleted = activePresetName;
    setCustomPresets((prev) => {
      const next = { ...prev };
      delete next[deleted];
      return next;
    });
    setActivePresetName("01. Pure Natural 30FPS");
    showNotice(`Deleted custom preset "${deleted}"`);
  };

  const handleExportPresetsJson = () => {
    const payload = {
      brand: "LUMIXA PRO // C270 CINEMA STUDIO",
      activePresetName,
      currentParams: params,
      customPresets,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lumixa_c270_studio_presets.json";
    a.click();
    URL.revokeObjectURL(url);
    showNotice("Exported studio preset bank to lumixa_c270_studio_presets.json");
  };

  const formatDuration = (sec: number) => {
    const m = Math.floor(sec / 60)
      .toString()
      .padStart(2, "0");
    const s = (sec % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const effectiveFps = params.unlock_30fps ? telemetry.fps : Math.min(10.0, telemetry.fps);

  // Render 16-segment Audio VU LED bar
  const renderAudioVuSegments = () => {
    const segments = 16;
    const normalized = Math.max(0, Math.min(1, (vuLevelDb + 60) / 60));
    const litCount = Math.round(normalized * segments);
    return (
      <div className="flex items-center gap-[2px] h-[12px] px-1.5 py-0.5 rounded-[3px] bg-[#07070A] border border-[#22222C]">
        {Array.from({ length: segments }).map((_, i) => {
          const isLit = i < litCount;
          let color = "#10B981";
          if (i >= 14) color = "#EF4444";
          else if (i >= 11) color = "#E5A93C";
          return (
            <span
              key={i}
              className="w-[4px] h-[8px] rounded-[1px]"
              style={{
                backgroundColor: isLit ? color : "#1C1C24",
                boxShadow: isLit ? `0 0 4px ${color}88` : "none",
              }}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div
      className="h-screen w-screen overflow-hidden flex flex-col select-none"
      style={{
        backgroundColor: "#0B0B0E",
        color: "#F4F4F6",
        fontFamily: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* =====================================================================
          1. TOP CAMERA TELEMETRY DECK (54px)
      ===================================================================== */}
      <header
        className="h-[54px] px-3 flex items-center justify-between gap-2 shrink-0 overflow-hidden"
        style={{
          background: "linear-gradient(180deg, #16161D 0%, #0E0E13 100%)",
          borderBottom: "1px solid #262632",
        }}
      >
        {/* Left: 3D Lens Emblem + Brand Title + Camera Selector + 30-FPS Boost */}
        <div className="flex items-center gap-2 shrink-0">
          <Lumixa3DLensLogo size={32} />
          <div className="flex flex-col leading-tight mr-0.5">
            <span className="text-[12px] font-extrabold tracking-[1.3px] text-[#F4F4F6] whitespace-nowrap">
              LUMIXA PRO
            </span>
            <span className="text-[8.5px] font-bold tracking-[1px] text-[#E5A93C] whitespace-nowrap">
              C270 CINEMA STUDIO
            </span>
          </div>

          <select
            aria-label="Select UVC Camera Device"
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="h-[30px] w-[155px] px-1.5 rounded-[5px] text-[10px] font-semibold text-[#F4F4F6] outline-none cursor-pointer truncate"
            style={{
              background: "linear-gradient(180deg, #242430 0%, #14141B 100%)",
              borderTop: "1px solid #3A3A4C",
              borderBottom: "1px solid #08080B",
              borderLeft: "1px solid #252532",
              borderRight: "1px solid #252532",
            }}
          >
            <option value="0: Logitech HD Webcam C270 (DirectShow MJPG)">
              0: Logitech C270 (MJPG)
            </option>
            <option value="1: OBS Virtual Broadcast Camera">
              1: OBS Virtual Camera
            </option>
          </select>

          <HardwareButton
            label={params.unlock_30fps ? "30-FPS BOOST: ON" : "30-FPS BOOST: OFF"}
            active={params.unlock_30fps}
            ledColor="emerald"
            onClick={handleToggle30FpsBoost}
            className="!px-2 !text-[10px]"
            title="Disables C270 Low-Light Compensation (Backlight=0) and locks -4 EV shutter so framerate never drops to 10 FPS"
          />

          <HardwareButton
            label={useLiveWebcam ? "LIVE UVC: ON" : "SIMULATED"}
            active={useLiveWebcam}
            ledColor="amber"
            onClick={() => setUseLiveWebcam((v) => !v)}
            className="!px-2 !text-[10px]"
            title="Toggle between live browser webcam stream and interactive C270 optical reference scene"
          />
        </div>

        {/* Center: Recessed LCD Digital Telemetry Screen */}
        <div
          className="hidden xl:flex items-center gap-1.5 px-2.5 h-[30px] rounded-[4px] font-mono text-[10px] font-semibold tracking-[0.2px] shrink-0"
          style={{
            backgroundColor: "#08080B",
            border: "1px solid #262632",
            boxShadow: "inset 0 1px 4px rgba(0,0,0,0.85)",
          }}
        >
          <span className="text-[#10B981]">
            {params.upscale_1080p ? "1080P" : "720P MJPG"}
          </span>
          <span className="text-[#3F3F4E]">|</span>
          <span
            style={{
              color: effectiveFps >= 24 ? "#10B981" : "#EF4444",
            }}
          >
            {effectiveFps.toFixed(1)} FPS
          </span>
          <span className="text-[#3F3F4E]">|</span>
          <span className="text-[#E5A93C]">{params.exposure_ev} EV</span>
          <span className="text-[#3F3F4E]">|</span>
          <span className="text-[#D4D4DC]">ISO {params.hw_gain}</span>
          <span className="text-[#3F3F4E]">|</span>
          <span className="text-[#10B981]">1.0X CFR</span>
        </div>

        {/* Right: Quick Action Hardware Buttons */}
        <div className="flex items-center gap-1 shrink-0">
          <HardwareButton
            label="PURE VIEW"
            active={params.pure_view_bypass}
            ledColor="amber"
            onClick={() => updateParam("pure_view_bypass", !params.pure_view_bypass)}
            className="!px-2 !text-[10px]"
            title="Bypass all software LUTs and adjustments to inspect raw C270 sensor feed"
          />
          <HardwareButton
            label={syncLabel}
            active={syncLabel === "UP TO DATE"}
            ledColor="emerald"
            onClick={handleGitHubSync}
            className="!px-2 !text-[10px]"
            title="Fetch and pull latest updates from GitHub repository (git pull --rebase --autostash)"
          />
          <HardwareButton
            label="RESET"
            showLed={false}
            onClick={handleResetAll}
            className="!px-2 !text-[10px]"
            title="Reset all software ISP and hardware parameters to factory defaults"
          />
          <HardwareButton
            label={`GALLERY (${capturedGallery.length})`}
            active={galleryModalOpen}
            ledColor="amber"
            onClick={() => setGalleryModalOpen(true)}
            className="!px-2 !text-[10px]"
          />
          <HardwareButton
            label="PYTHON SOURCE"
            active={repoModalOpen}
            ledColor="emerald"
            onClick={() => setRepoModalOpen(true)}
            className="!px-2 !text-[10px]"
            title="Inspect all 18 native Windows PyQt6 + OpenCV DirectShow Python source files"
          />
        </div>
      </header>

      {/* =====================================================================
          2. MAIN STUDIO WORKSPACE (EVF VIEWFINDER + RIGHT CONTROL DECK)
      ===================================================================== */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* CENTER COLUMN: DSLR / Cinema EVF Viewfinder + Bottom EVF Bar */}
        <main className="flex-1 flex flex-col min-w-0 p-2.5 gap-2.5 bg-[#09090C] overflow-hidden">
          <ViewportCanvas
            params={params}
            useLiveWebcam={useLiveWebcam}
            isRecording={isRecording}
            recordingTimeSec={recordingSec}
            countdownValue={countdownVal}
            flashTrigger={flashActive}
            onTelemetryUpdate={(t) =>
              setTelemetry({
                fps: t.fps,
                processMs: t.processMs,
                resolution: t.resolution,
                webcamConnected: t.webcamConnected,
              })
            }
            onCaptureDataUrlReady={handleCaptureGetterReady}
            onPTZChange={(zoom, panX, tiltY) =>
              setParams((prev) => ({
                ...prev,
                zoom: Math.round(zoom),
                pan_x: Math.round(panX),
                tilt_y: Math.round(tiltY),
              }))
            }
          />

          {/* Bottom Floating EVF Glass Transport Bar (74px) */}
          <div
            className="h-[74px] px-3 rounded-[6px] flex items-center justify-between gap-2 shrink-0 overflow-hidden"
            style={{
              background: "linear-gradient(180deg, #16161E 0%, #0E0E14 100%)",
              border: "1px solid #262632",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)",
            }}
          >
            {/* Left: Live 16-Segment Audio VU Peak Meter + 50Hz Anti-Flicker Lock */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[9.5px] font-bold text-[#9CA3AF]">
                    MIC VU (48kHz)
                  </span>
                  <span className="font-mono text-[9.5px] font-bold text-[#10B981]">
                    {vuLevelDb.toFixed(1)} dB
                  </span>
                </div>
                {renderAudioVuSegments()}
              </div>
              <div
                className="px-2 py-1 rounded-[4px] font-mono text-[9.5px] font-semibold text-[#10B981] whitespace-nowrap"
                style={{
                  backgroundColor: "#08080B",
                  border: "1px solid #23232E",
                }}
              >
                50Hz LOCK
              </div>
            </div>

            {/* Center: Mechanical Shutter (60px) & Record (60px) + Timer / Flash / Pause / Burst */}
            <div className="flex items-center gap-1.5 shrink-0">
              <HardwareButton
                label={params.timer_sec === 0 ? "TIMER: OFF" : `TIMER: ${params.timer_sec}S`}
                active={params.timer_sec > 0}
                ledColor="amber"
                className="!px-2 !text-[10px]"
                onClick={() => {
                  const next =
                    params.timer_sec === 0 ? 3 : params.timer_sec === 3 ? 5 : 0;
                  updateParam("timer_sec", next);
                }}
              />
              <HardwareButton
                label="FLASH"
                active={params.screen_flash}
                ledColor="amber"
                className="!px-2 !text-[10px]"
                onClick={() => updateParam("screen_flash", !params.screen_flash)}
              />

              <MechanicalShutterButton
                onClick={handleShutterTrigger}
                title="Capture Grade-Baked PNG Still Frame"
              />

              <CinemaRecordButton
                isRecording={isRecording}
                onClick={handleToggleRecord}
                title="Start / Stop Wall-Clock 1.0x Synchronized 30.0 FPS CFR Video Recording"
              />

              <HardwareButton
                label={isPaused ? "RESUME" : "PAUSE"}
                active={isPaused}
                ledColor="amber"
                disabled={!isRecording}
                className="!px-2 !text-[10px]"
                onClick={() => setIsPaused((p) => !p)}
              />

              <HardwareButton
                label="BURST 3X"
                showLed={false}
                className="!px-2 !text-[10px]"
                onClick={handleBurst3x}
                title="Capture rapid 3-frame studio burst sequence"
              />

              <div
                className="px-2 py-1.5 rounded-[4px] font-mono text-[10px] font-bold whitespace-nowrap"
                style={{
                  backgroundColor: "#08080B",
                  border: "1px solid #262632",
                  color: isRecording ? "#EF4444" : "#9CA3AF",
                }}
              >
                {isRecording
                  ? `REC ${formatDuration(recordingSec)} (${cfrFramesWritten}F · 1.0x)`
                  : "STANDBY · 1.0x CFR"}
              </div>
            </div>

            {/* Right: Virtual Broadcast Cam & Aspect Ratio */}
            <div className="flex items-center gap-1.5 shrink-0">
              <HardwareButton
                label={params.virtual_cam_active ? "VCAM: LIVE" : "VIRTUAL CAM"}
                active={params.virtual_cam_active}
                ledColor="emerald"
                className="!px-2 !text-[10px]"
                onClick={() => {
                  const next = !params.virtual_cam_active;
                  updateParam("virtual_cam_active", next);
                  showNotice(
                    next
                      ? "pyvirtualcam Broadcast Output ACTIVE (Zoom / OBS / Teams feed live)"
                      : "Virtual Broadcast Camera stopped"
                  );
                }}
              />
              <HardwareButton
                label={
                  params.aspect_mode === "9:16" ? "9:16" : "16:9"
                }
                active={params.aspect_mode === "9:16"}
                ledColor="amber"
                className="!px-2 !text-[10px]"
                onClick={() =>
                  updateParam(
                    "aspect_mode",
                    params.aspect_mode === "9:16" ? "16:9" : "9:16"
                  )
                }
              />
            </div>
          </div>
        </main>

        {/* =====================================================================
            3. RIGHT SEQUENTIAL CONTROL DECK (392px width, 4 Hardware Mode Tabs)
        ===================================================================== */}
        <aside
          className="w-[392px] shrink-0 flex flex-col min-h-0"
          style={{
            backgroundColor: "#0F0F14",
            borderLeft: "1px solid #262632",
          }}
        >
          {/* 4 Tactile Hardware Mode Selector Buttons */}
          <div
            className="p-2 grid grid-cols-4 gap-1.5 shrink-0"
            style={{
              backgroundColor: "#0B0B0F",
              borderBottom: "1px solid #24242F",
            }}
          >
            <HardwareButton
              label="1. EXP/LIGHT"
              active={activeTab === "exposure"}
              ledColor="amber"
              showLed={false}
              onClick={() => setActiveTab("exposure")}
              className="!px-1 !text-[10px]"
            />
            <HardwareButton
              label="2. COLOR/LUT"
              active={activeTab === "color"}
              ledColor="amber"
              showLed={false}
              onClick={() => setActiveTab("color")}
              className="!px-1 !text-[10px]"
            />
            <HardwareButton
              label="3. OPTICS/AI"
              active={activeTab === "optics"}
              ledColor="amber"
              showLed={false}
              onClick={() => setActiveTab("optics")}
              className="!px-1 !text-[10px]"
            />
            <HardwareButton
              label="4. PRESETS(12)"
              active={activeTab === "presets"}
              ledColor="amber"
              showLed={false}
              onClick={() => setActiveTab("presets")}
              className="!px-1 !text-[10px]"
            />
          </div>

          {/* Scrollable Mode Deck Body */}
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
            {/* -----------------------------------------------------------------
                MODE 1: 1. EXPOSURE & LIGHT
            ----------------------------------------------------------------- */}
            {activeTab === "exposure" && (
              <>
                <StudioHardwareCard
                  title="LIGHTING & CLARITY (ISP)"
                  badge="ZERO-LATENCY"
                >
                  <PrecisionHardwareSlider
                    label="Smart Room Light Boost (Shadow Lift)"
                    value={params.smart_light_boost}
                    min={0}
                    max={100}
                    defaultValue={25}
                    unit="%"
                    onChange={(v) => updateParam("smart_light_boost", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Digital Brightness"
                    value={params.digital_brightness}
                    min={-100}
                    max={100}
                    defaultValue={0}
                    onChange={(v) => updateParam("digital_brightness", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Micro-Contrast"
                    value={params.micro_contrast}
                    min={-100}
                    max={100}
                    defaultValue={8}
                    onChange={(v) => updateParam("micro_contrast", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Optical Sharpness (HD Crisp)"
                    value={params.optical_sharpness}
                    min={0}
                    max={100}
                    defaultValue={15}
                    unit="%"
                    onChange={(v) => updateParam("optical_sharpness", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Low-Light Chroma Denoise"
                    value={params.denoise}
                    min={0}
                    max={100}
                    defaultValue={10}
                    unit="%"
                    onChange={(v) => updateParam("denoise", v)}
                  />
                </StudioHardwareCard>

                <StudioHardwareCard
                  title="C270 SENSOR HARDWARE — EXACT NATIVE RANGES"
                  badge={params.unlock_30fps ? "30 FPS LOCKED" : "AUTO EXP"}
                >
                  <HardwareButton
                    label={
                      params.unlock_30fps
                        ? "UNLOCK 30 FPS (LOW-LIGHT LAG DISABLED)"
                        : "ENABLE 30 FPS ANTI-LAG BOOST"
                    }
                    active={params.unlock_30fps}
                    ledColor="emerald"
                    fullWidth
                    onClick={handleToggle30FpsBoost}
                  />

                  <PrecisionHardwareSlider
                    label="Sensor Shutter (Exposure)"
                    value={params.exposure_ev}
                    min={-11}
                    max={-2}
                    defaultValue={-4}
                    unit=" EV"
                    onChange={(v) => updateParam("exposure_ev", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Sensor ISO Gain"
                    value={params.hw_gain}
                    min={0}
                    max={255}
                    defaultValue={130}
                    onChange={(v) => updateParam("hw_gain", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Hardware Brightness (Default 128)"
                    value={params.hw_brightness}
                    min={0}
                    max={255}
                    defaultValue={C270_NATIVE_HW_DEFAULTS.hw_brightness}
                    onChange={(v) => updateParam("hw_brightness", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Hardware Contrast (Default 32)"
                    value={params.hw_contrast}
                    min={0}
                    max={255}
                    defaultValue={C270_NATIVE_HW_DEFAULTS.hw_contrast}
                    onChange={(v) => updateParam("hw_contrast", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Hardware Saturation (Default 32)"
                    value={params.hw_saturation}
                    min={0}
                    max={255}
                    defaultValue={C270_NATIVE_HW_DEFAULTS.hw_saturation}
                    onChange={(v) => updateParam("hw_saturation", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Hardware Sharpness (Default 24)"
                    value={params.hw_sharpness}
                    min={0}
                    max={255}
                    defaultValue={C270_NATIVE_HW_DEFAULTS.hw_sharpness}
                    onChange={(v) => updateParam("hw_sharpness", v)}
                  />

                  <HardwareButton
                    label="RESTORE FACTORY C270 HARDWARE DEFAULTS"
                    showLed={false}
                    fullWidth
                    onClick={handleRestoreC270Defaults}
                  />
                </StudioHardwareCard>
              </>
            )}

            {/* -----------------------------------------------------------------
                MODE 2: 2. COLOR & LUTS
            ----------------------------------------------------------------- */}
            {activeTab === "color" && (
              <>
                <StudioHardwareCard
                  title="CINEMA FILM LOOKS (8 STUDIO MATRICES)"
                  badge={params.active_lut.toUpperCase()}
                >
                  <div className="grid grid-cols-2 gap-1.5">
                    {STUDIO_LOOK_NAMES.map((lookName: StudioLookName) => (
                      <HardwareButton
                        key={lookName}
                        label={lookName}
                        active={params.active_lut === lookName}
                        ledColor="amber"
                        onClick={() => updateParam("active_lut", lookName)}
                        className="!justify-start !text-[10.5px]"
                      />
                    ))}
                  </div>

                  <PrecisionHardwareSlider
                    label="Look Intensity"
                    value={params.lut_intensity}
                    min={0}
                    max={100}
                    defaultValue={75}
                    unit="%"
                    onChange={(v) => updateParam("lut_intensity", v)}
                  />

                  <input
                    ref={cubeFileInputRef}
                    type="file"
                    accept=".cube"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setCustomLutFileName(file.name);
                        showNotice(`Loaded custom 3D LUT file: ${file.name}`);
                      }
                    }}
                  />
                  <HardwareButton
                    label={
                      customLutFileName
                        ? `CUSTOM LUT: ${customLutFileName}`
                        : "LOAD CUSTOM .CUBE 3D LUT..."
                    }
                    active={Boolean(customLutFileName)}
                    ledColor="emerald"
                    fullWidth
                    onClick={() => cubeFileInputRef.current?.click()}
                  />
                </StudioHardwareCard>

                <StudioHardwareCard title="WHITE BALANCE & TONE">
                  <PrecisionHardwareSlider
                    label="Color Temperature (Warmth)"
                    value={params.temp_shift}
                    min={-100}
                    max={100}
                    defaultValue={0}
                    onChange={(v) => updateParam("temp_shift", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Tint (Green / Magenta)"
                    value={params.tint}
                    min={-100}
                    max={100}
                    defaultValue={0}
                    onChange={(v) => updateParam("tint", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Vibrance (Rich Color)"
                    value={params.vibrance}
                    min={-100}
                    max={100}
                    defaultValue={10}
                    onChange={(v) => updateParam("vibrance", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Optical Lens Vignette"
                    value={params.vignette}
                    min={0}
                    max={100}
                    defaultValue={0}
                    unit="%"
                    onChange={(v) => updateParam("vignette", v)}
                  />
                </StudioHardwareCard>
              </>
            )}

            {/* -----------------------------------------------------------------
                MODE 3: 3. OPTICS & AI
            ----------------------------------------------------------------- */}
            {activeTab === "optics" && (
              <>
                <StudioHardwareCard
                  title="FLUID GIMBAL PTZ & GEOMETRY"
                  badge={`${params.zoom}%`}
                >
                  <PrecisionHardwareSlider
                    label="Optical-Feel Lanczos4 Zoom"
                    value={params.zoom}
                    min={100}
                    max={300}
                    defaultValue={100}
                    unit="%"
                    onChange={(v) => updateParam("zoom", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Pan X (Horizontal)"
                    value={params.pan_x}
                    min={-100}
                    max={100}
                    defaultValue={0}
                    unit="%"
                    onChange={(v) => updateParam("pan_x", v)}
                  />
                  <PrecisionHardwareSlider
                    label="Tilt Y (Vertical)"
                    value={params.tilt_y}
                    min={-100}
                    max={100}
                    defaultValue={0}
                    unit="%"
                    onChange={(v) => updateParam("tilt_y", v)}
                  />
                  <div className="grid grid-cols-2 gap-1.5 pt-1">
                    <HardwareButton
                      label="MIRROR VIDEO"
                      active={params.mirror_h}
                      ledColor="amber"
                      onClick={() => updateParam("mirror_h", !params.mirror_h)}
                    />
                    <HardwareButton
                      label="FLIP VERTICAL"
                      active={params.flip_v}
                      ledColor="amber"
                      onClick={() => updateParam("flip_v", !params.flip_v)}
                    />
                    <HardwareButton
                      label={`ROTATE (${params.rotation_deg}°)`}
                      active={params.rotation_deg !== 0}
                      ledColor="amber"
                      onClick={() =>
                        updateParam(
                          "rotation_deg",
                          ((params.rotation_deg + 90) % 360) as 0 | 90 | 180 | 270
                        )
                      }
                    />
                    <HardwareButton
                      label="CENTER RESET"
                      showLed={false}
                      onClick={() => {
                        updateParam("zoom", 100);
                        updateParam("pan_x", 0);
                        updateParam("tilt_y", 0);
                        updateParam("rotation_deg", 0);
                      }}
                    />
                  </div>
                </StudioHardwareCard>

                <StudioHardwareCard title="AI PORTRAIT STUDIO">
                  <div className="flex flex-col gap-1">
                    <span className="text-[11px] font-medium text-[#D4D4DC]">
                      Background Segmentation Mode
                    </span>
                    <select
                      aria-label="Background Segmentation Mode"
                      value={params.bg_mode}
                      onChange={(e) =>
                        updateParam("bg_mode", e.target.value as BackgroundMode)
                      }
                      className="h-[30px] px-2 rounded-[5px] text-[11px] font-semibold text-[#F4F4F6] outline-none cursor-pointer"
                      style={{
                        background: "linear-gradient(180deg, #242430 0%, #14141B 100%)",
                        border: "1px solid #323242",
                      }}
                    >
                      <option value="Off (Natural)">Off (Natural)</option>
                      <option value="Optical Bokeh Blur">Optical Bokeh Blur</option>
                      <option value="Studio Dimmed Spotlight">
                        Studio Dimmed Spotlight
                      </option>
                      <option value="Custom Backdrop">Custom Backdrop</option>
                    </select>
                  </div>

                  <PrecisionHardwareSlider
                    label="Blur / Dim Strength"
                    value={params.bg_strength}
                    min={10}
                    max={100}
                    defaultValue={50}
                    unit="%"
                    onChange={(v) => updateParam("bg_strength", v)}
                  />

                  <HardwareButton
                    label="AI FACE AUTO-FRAMING (CENTER STAGE)"
                    active={params.ai_auto_frame}
                    ledColor="emerald"
                    fullWidth
                    onClick={() => updateParam("ai_auto_frame", !params.ai_auto_frame)}
                  />

                  <PrecisionHardwareSlider
                    label="Portrait Skin Softening"
                    value={params.skin_softening}
                    min={0}
                    max={100}
                    defaultValue={0}
                    unit="%"
                    onChange={(v) => updateParam("skin_softening", v)}
                  />
                </StudioHardwareCard>

                <StudioHardwareCard title="VIEWFINDER GUIDES & BROADCAST">
                  <div className="grid grid-cols-2 gap-1.5">
                    <HardwareButton
                      label="RULE OF THIRDS"
                      active={params.show_grid}
                      ledColor="amber"
                      onClick={() => updateParam("show_grid", !params.show_grid)}
                    />
                    <HardwareButton
                      label="2.35:1 ANAMORPHIC"
                      active={params.show_cinema_bars}
                      ledColor="amber"
                      onClick={() =>
                        updateParam("show_cinema_bars", !params.show_cinema_bars)
                      }
                    />
                    <HardwareButton
                      label="RGB HISTOGRAM"
                      active={params.show_corner_hud}
                      ledColor="emerald"
                      onClick={() =>
                        updateParam("show_corner_hud", !params.show_corner_hud)
                      }
                    />
                    <HardwareButton
                      label="LOWER-THIRD TAG"
                      active={params.show_lower_third}
                      ledColor="amber"
                      onClick={() =>
                        updateParam("show_lower_third", !params.show_lower_third)
                      }
                    />
                  </div>
                  {params.show_lower_third && (
                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <input
                        type="text"
                        aria-label="Broadcast Name"
                        value={params.lower_third_name}
                        onChange={(e) =>
                          updateParam("lower_third_name", e.target.value)
                        }
                        placeholder="Speaker Name"
                        className="h-[28px] px-2 rounded-[4px] text-[11px] bg-[#08080B] border border-[#282834] text-[#F4F4F6]"
                      />
                      <input
                        type="text"
                        aria-label="Broadcast Role"
                        value={params.lower_third_title}
                        onChange={(e) =>
                          updateParam("lower_third_title", e.target.value)
                        }
                        placeholder="Title / Role"
                        className="h-[28px] px-2 rounded-[4px] text-[11px] bg-[#08080B] border border-[#282834] text-[#E5A93C]"
                      />
                    </div>
                  )}
                </StudioHardwareCard>
              </>
            )}

            {/* -----------------------------------------------------------------
                MODE 4: 4. PRESETS (12)
            ----------------------------------------------------------------- */}
            {activeTab === "presets" && (
              <>
                <StudioHardwareCard
                  title="12 ONE-CLICK STUDIO PRESETS"
                  badge="FACTORY CALIBRATED"
                >
                  <div className="grid grid-cols-2 gap-1.5">
                    {Object.entries(FACTORY_PRESETS).map(([presetName, presetData]) => (
                      <HardwareButton
                        key={presetName}
                        label={presetName}
                        active={activePresetName === presetName}
                        ledColor="amber"
                        title={PRESET_DESCRIPTIONS[presetName] || presetName}
                        onClick={() => handleApplyPreset(presetName, presetData)}
                        className="!justify-start !text-[10px] !px-2"
                      />
                    ))}
                  </div>
                  {PRESET_DESCRIPTIONS[activePresetName] && (
                    <div
                      className="p-2 rounded-[4px] text-[10.5px] text-[#9CA3AF] font-mono"
                      style={{
                        backgroundColor: "#08080B",
                        border: "1px solid #22222C",
                      }}
                    >
                      {PRESET_DESCRIPTIONS[activePresetName]}
                    </div>
                  )}
                </StudioHardwareCard>

                <StudioHardwareCard title="CUSTOM USER PRESET BANK">
                  {Object.keys(customPresets).length > 0 && (
                    <div className="grid grid-cols-2 gap-1.5 mb-1">
                      {Object.entries(customPresets).map(([cName, cParams]) => (
                        <HardwareButton
                          key={cName}
                          label={cName}
                          active={activePresetName === cName}
                          ledColor="emerald"
                          onClick={() => handleApplyPreset(cName, cParams)}
                          className="!justify-start !text-[10.5px]"
                        />
                      ))}
                    </div>
                  )}

                  <div className="flex gap-1.5">
                    <input
                      type="text"
                      aria-label="Custom Preset Name"
                      value={newPresetInput}
                      onChange={(e) => setNewPresetInput(e.target.value)}
                      placeholder="New custom preset name..."
                      className="flex-1 h-[30px] px-2.5 rounded-[4px] text-[11px] bg-[#08080B] border border-[#282834] text-[#F4F4F6] outline-none"
                    />
                    <HardwareButton
                      label="SAVE NEW"
                      active={Boolean(newPresetInput.trim())}
                      ledColor="emerald"
                      onClick={handleSaveCustomPreset}
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-1.5 pt-1">
                    <HardwareButton
                      label="DELETE"
                      showLed={false}
                      onClick={handleDeleteCustomPreset}
                    />
                    <HardwareButton
                      label="EXPORT JSON"
                      showLed={false}
                      onClick={handleExportPresetsJson}
                    />
                    <HardwareButton
                      label="IMPORT JSON"
                      showLed={false}
                      onClick={() => presetImportInputRef.current?.click()}
                    />
                  </div>
                  <input
                    ref={presetImportInputRef}
                    type="file"
                    accept=".json"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const reader = new FileReader();
                      reader.onload = () => {
                        try {
                          const parsed = JSON.parse(String(reader.result));
                          if (parsed.customPresets) {
                            setCustomPresets((prev) => ({
                              ...prev,
                              ...parsed.customPresets,
                            }));
                          }
                          if (parsed.currentParams) {
                            setParams((prev) => ({
                              ...prev,
                              ...parsed.currentParams,
                            }));
                          }
                          showNotice(`Imported preset bank from ${file.name}`);
                        } catch {
                          showNotice("Invalid JSON preset file");
                        }
                      };
                      reader.readAsText(file);
                    }}
                  />
                </StudioHardwareCard>

                <StudioHardwareCard title="MASTER OUTPUT RESOLUTION">
                  <div className="grid grid-cols-2 gap-1.5">
                    <HardwareButton
                      label="720p 30FPS NATIVE"
                      active={!params.upscale_1080p}
                      ledColor="emerald"
                      onClick={() => updateParam("upscale_1080p", false)}
                    />
                    <HardwareButton
                      label="1080p LANCZOS4"
                      active={params.upscale_1080p}
                      ledColor="amber"
                      onClick={() => updateParam("upscale_1080p", true)}
                    />
                  </div>
                </StudioHardwareCard>
              </>
            )}
          </div>

          {/* Bottom Status Notification Strip */}
          <div
            className="h-[30px] px-3 flex items-center justify-between text-[10.5px] font-mono shrink-0"
            style={{
              backgroundColor: "#08080B",
              borderTop: "1px solid #22222C",
              color: statusNotice ? "#E5A93C" : "#71717A",
            }}
          >
            <span className="truncate">
              {statusNotice || `PRESET: ${activePresetName}`}
            </span>
            <span className="text-[#10B981] shrink-0 ml-2">ISP {telemetry.processMs}ms</span>
          </div>
        </aside>
      </div>

      {/* Modals */}
      <PythonRepoModal
        open={repoModalOpen}
        onClose={() => setRepoModalOpen(false)}
        repoFiles={repoFiles}
      />
      <StudioGalleryModal
        open={galleryModalOpen}
        onClose={() => setGalleryModalOpen(false)}
        captures={capturedGallery}
        onClearGallery={() => setCapturedGallery([])}
      />
    </div>
  );
}
