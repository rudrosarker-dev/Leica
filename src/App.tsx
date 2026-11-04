/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from "react";
import {
  StudioParams,
  DEFAULT_STUDIO_PARAMS,
  FACTORY_PRESETS,
  FILM_LOOK_NAMES,
  AIStudioMode,
  getFpsBadgeColor,
  formatMasterTimecode,
  parseCubeLUTText,
} from "./utils/ispMath";
import {
  ApertureLogoSvg,
  RefreshIconSvg,
  InspectorCard,
  PrecisionSlider,
  ToggleSwitch,
  SegmentedBar,
  ShutterReleaseButton,
  CinemaRecordButton,
  PauseRecordButton,
} from "./components/StudioWidgets";
import { ViewportCanvas } from "./components/ViewportCanvas";
import {
  PythonRepoModal,
  StudioGalleryModal,
  RepoFileEntry,
  CapturedItem,
} from "./components/PythonRepoModal";

export default function App() {
  // Core Studio Parameters State
  const [params, setParams] = useState<StudioParams>(() => ({
    ...DEFAULT_STUDIO_PARAMS,
  }));

  // Presets State
  const [userPresets, setUserPresets] = useState<Record<string, StudioParams>>({});
  const [activePresetName, setActivePresetName] = useState<string>(
    "1. C270 30FPS Low-Light Fix"
  );
  const [savingPresetMode, setSavingPresetMode] = useState<boolean>(false);
  const [newPresetTitle, setNewPresetTitle] = useState<string>("Custom C270 Look");

  // Hardware & Top Bar State
  const [deviceList, setDeviceList] = useState<string[]>([
    "USB Video Device #0 (C270 HD)",
    "Logitech HD Webcam C270 (UVC)",
  ]);
  const [selectedDevice, setSelectedDevice] = useState<string>(
    "USB Video Device #0 (C270 HD)"
  );
  const [driverBackend, setDriverBackend] = useState<"DirectShow" | "MSMF">(
    "DirectShow"
  );
  const [showDriverSheetModal, setShowDriverSheetModal] = useState<boolean>(false);

  // Right Dock Tab Index: 0 = COLOR & LUT, 1 = AI STUDIO, 2 = OVERLAYS
  const [rightTabIndex, setRightTabIndex] = useState<number>(0);

  // Telemetry & Transport State
  const [liveFps, setLiveFps] = useState<number>(30.0);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isPausedRecording, setIsPausedRecording] = useState<boolean>(false);
  const [recordedFrames, setRecordedFrames] = useState<number>(0);
  const [tallyBlinkOn, setTallyBlinkOn] = useState<boolean>(true);
  const [isVirtualCam, setIsVirtualCam] = useState<boolean>(false);

  const [timerMode, setTimerMode] = useState<string>("Timer: Off");
  const [flashEnabled, setFlashEnabled] = useState<boolean>(false);
  const [snapshotFormat, setSnapshotFormat] = useState<string>("PNG Lossless");
  const [countdownValue, setCountdownValue] = useState<number>(0);
  const [flashTriggerCounter, setFlashTriggerCounter] = useState<number>(0);
  const [captureRequestCounter, setCaptureRequestCounter] = useState<number>(0);

  // Loaded Assets (.cube, backdrop image, watermark PNG)
  const [customCubeLut, setCustomCubeLut] = useState<{
    r: Float32Array;
    g: Float32Array;
    b: Float32Array;
  } | null>(null);
  const [backdropImageEl, setBackdropImageEl] = useState<HTMLImageElement | null>(
    null
  );
  const [watermarkImageEl, setWatermarkImageEl] = useState<HTMLImageElement | null>(
    null
  );

  // Modals & Repository Inspector State
  const [repoFiles, setRepoFiles] = useState<RepoFileEntry[]>([]);
  const [showRepoModal, setShowRepoModal] = useState<boolean>(false);
  const [showGalleryModal, setShowGalleryModal] = useState<boolean>(false);
  const [capturedItems, setCapturedItems] = useState<CapturedItem[]>([]);
  const [statusBanner, setStatusBanner] = useState<string>(
    "DIRECTSHOW UVC PIPELINE LOCKED @ 30.0 FPS"
  );

  // Hidden File Inputs
  const cubeInputRef = useRef<HTMLInputElement | null>(null);
  const backdropInputRef = useRef<HTMLInputElement | null>(null);
  const watermarkInputRef = useRef<HTMLInputElement | null>(null);
  const colorPickerInputRef = useRef<HTMLInputElement | null>(null);

  // Fetch generated Python Desktop Repository files from server
  useEffect(() => {
    fetch("/api/repo-files")
      .then((r) => r.json())
      .then((data) => {
        if (data && Array.isArray(data.files)) {
          setRepoFiles(data.files);
        }
      })
      .catch(() => {});
  }, []);

  // Recording Timecode & Blinking Tally Dot Timer
  useEffect(() => {
    if (!isRecording || isPausedRecording) {
      setTallyBlinkOn(false);
      return;
    }
    setTallyBlinkOn(true);
    const frameInterval = setInterval(() => {
      setRecordedFrames((prev) => prev + 1);
    }, 1000 / 30);

    const blinkInterval = setInterval(() => {
      setTallyBlinkOn((prev) => !prev);
    }, 500);

    return () => {
      clearInterval(frameInterval);
      clearInterval(blinkInterval);
    };
  }, [isRecording, isPausedRecording]);

  const updateParam = <K extends keyof StudioParams>(
    key: K,
    val: StudioParams[K]
  ) => {
    setParams((prev) => ({ ...prev, [key]: val }));
  };

  const handleRefreshDevices = async () => {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const list = await navigator.mediaDevices.enumerateDevices();
        const videoDevs = list
          .filter((d) => d.kind === "videoinput")
          .map((d, i) => d.label || `USB Video Device #${i} (C270 HD)`);
        if (videoDevs.length > 0) {
          setDeviceList(videoDevs);
          setSelectedDevice(videoDevs[0]);
        }
      }
      setStatusBanner("UVC BUS RESCANNED // DIRECTSHOW 30FPS READY");
    } catch {
      setStatusBanner("UVC BUS RESCANNED // DEFAULT C270 PROFILE ACTIVE");
    }
  };

  const handleSelectPreset = (name: string) => {
    setActivePresetName(name);
    const target = userPresets[name] || FACTORY_PRESETS[name];
    if (target) {
      setParams({ ...target });
      setStatusBanner(`LOADED PRESET: ${name.toUpperCase()}`);
    }
  };

  const handleSaveCustomPreset = () => {
    const clean = newPresetTitle.trim();
    if (!clean) return;
    setUserPresets((prev) => ({ ...prev, [clean]: { ...params } }));
    setActivePresetName(clean);
    setSavingPresetMode(false);
    setStatusBanner(`SAVED USER PRESET: ${clean.toUpperCase()}`);
  };

  const handleDeletePreset = () => {
    if (userPresets[activePresetName]) {
      const copy = { ...userPresets };
      delete copy[activePresetName];
      setUserPresets(copy);
      const firstFactory = Object.keys(FACTORY_PRESETS)[0];
      handleSelectPreset(firstFactory);
      setStatusBanner(`DELETED PRESET: ${activePresetName.toUpperCase()}`);
    } else {
      setStatusBanner("FACTORY CALIBRATION PRESETS ARE PROTECTED");
    }
  };

  const handleResetAll = () => {
    setParams({ ...DEFAULT_STUDIO_PARAMS });
    setCustomCubeLut(null);
    setStatusBanner("ALL STUDIO PARAMETERS RESET TO DEFAULT CALIBRATION");
  };

  // Transport: Shutter Release, Countdown, Softbox Flash, Burst 3x
  const executeImmediateCapture = () => {
    if (flashEnabled) {
      setFlashTriggerCounter((c) => c + 1);
      setTimeout(() => {
        setCaptureRequestCounter((c) => c + 1);
      }, 240);
    } else {
      setCaptureRequestCounter((c) => c + 1);
    }
  };

  const handleShutterRelease = () => {
    let sec = 0;
    if (timerMode === "3s Timer") sec = 3;
    else if (timerMode === "5s Timer") sec = 5;
    else if (timerMode === "10s Timer") sec = 10;

    if (sec === 0) {
      executeImmediateCapture();
      return;
    }

    setCountdownValue(sec);
    let rem = sec;
    const iv = setInterval(() => {
      rem -= 1;
      if (rem > 0) {
        setCountdownValue(rem);
      } else {
        clearInterval(iv);
        setCountdownValue(0);
        executeImmediateCapture();
      }
    }, 1000);
  };

  const handleBurst3x = () => {
    setStatusBanner("BURST 3X CAPTURE TRIGGERED (180MS INTERVAL)");
    setCaptureRequestCounter((c) => c + 1);
    setTimeout(() => setCaptureRequestCounter((c) => c + 1), 180);
    setTimeout(() => setCaptureRequestCounter((c) => c + 1), 360);
  };

  const handleFrameCaptured = (dataUrl: string, width: number, height: number) => {
    const now = new Date();
    const ts = now.toTimeString().slice(0, 8).replace(/:/g, "-");
    const newItem: CapturedItem = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      timestamp: ts,
      format: snapshotFormat,
      resolution: `${width}x${height}`,
      dataUrl,
    };
    setCapturedItems((prev) => [newItem, ...prev]);
    setStatusBanner(`SAVED STILL (${width}x${height} ${snapshotFormat})`);
  };

  const handleToggleRecord = () => {
    if (!isRecording) {
      setRecordedFrames(0);
      setIsPausedRecording(false);
      setIsRecording(true);
      setStatusBanner("RECORDING MASTER MP4 + 44.1KHZ WAV AUDIO");
    } else {
      setIsRecording(false);
      setIsPausedRecording(false);
      setRecordedFrames(0);
      setStatusBanner("MUXED MP4 + AAC 192K SAVED TO ~/Pictures/C270_Optix_Studio");
    }
  };

  const handleCubeFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const txt = String(reader.result || "");
      const res = parseCubeLUTText(txt);
      if (res.valid) {
        setCustomCubeLut({ r: res.r, g: res.g, b: res.b });
        updateParam("custom_cube_name", file.name);
        setStatusBanner(res.message.toUpperCase());
      } else {
        setStatusBanner(res.message.toUpperCase());
      }
    };
    reader.readAsText(file);
  };

  const handleBackdropFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      setBackdropImageEl(img);
      updateParam("ai_mode", "Custom Studio Backdrop");
      setStatusBanner(`LOADED STUDIO BACKDROP: ${file.name.toUpperCase()}`);
    };
    img.src = url;
  };

  const handleWatermarkFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      setWatermarkImageEl(img);
      updateParam("show_watermark", true);
      setStatusBanner(`LOADED PNG WATERMARK: ${file.name.toUpperCase()}`);
    };
    img.src = url;
  };

  const presetNames = [
    ...Object.keys(FACTORY_PRESETS),
    ...Object.keys(userPresets),
  ];

  const shortLutBadge = params.custom_cube_name
    ? params.custom_cube_name.replace(/\.cube$/i, "").toUpperCase().slice(0, 12)
    : params.film_look
        .toUpperCase()
        .replace("KODAK ", "")
        .replace("LEICA ", "");

  return (
    <div
      className="w-screen h-screen flex flex-col overflow-hidden select-none"
      style={{ backgroundColor: "#070709", color: "#F4F4F6" }}
    >
      {/* Hidden File Upload Inputs */}
      <input
        ref={cubeInputRef}
        type="file"
        accept=".cube,.CUBE"
        className="hidden"
        onChange={handleCubeFileUpload}
      />
      <input
        ref={backdropInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleBackdropFileUpload}
      />
      <input
        ref={watermarkInputRef}
        type="file"
        accept="image/png"
        className="hidden"
        onChange={handleWatermarkFileUpload}
      />
      <input
        ref={colorPickerInputRef}
        type="color"
        value={params.backdrop_color_hex}
        className="hidden"
        onChange={(e) => {
          setBackdropImageEl(null);
          updateParam("backdrop_color_hex", e.target.value);
          updateParam("ai_mode", "Custom Studio Backdrop");
        }}
      />

      {/* =====================================================================
          ZONE A — Top Telemetry & Hardware Bar (Fixed Height: 46px)
      ===================================================================== */}
      <header
        className="h-[46px] px-[14px] flex items-center justify-between gap-[8px] shrink-0"
        style={{
          backgroundColor: "#0A0A0D",
          borderBottom: "1px solid #22222B",
        }}
      >
        {/* Left Cluster */}
        <div className="flex items-center gap-[8px] shrink-0">
          <ApertureLogoSvg size={20} />
          <span
            className="text-[12px] font-bold tracking-[1.4px] whitespace-nowrap shrink-0"
            style={{ color: "#F4F4F6" }}
          >
            LEICA // C270 OPTIX STUDIO
          </span>

          <div className="w-[1px] h-[22px] bg-[#262630] shrink-0" />

          <select
            aria-label="Camera Device Selector"
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="w-[156px] h-[28px] px-2 rounded-[4px] text-[11px] font-medium truncate cursor-pointer focus:outline-none"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            {deviceList.map((dev) => (
              <option key={dev} value={dev}>
                {dev}
              </option>
            ))}
          </select>

          <button
            type="button"
            aria-label="Refresh Camera Devices"
            title="Rescan USB UVC Camera Devices"
            onClick={handleRefreshDevices}
            className="w-[28px] h-[28px] rounded-[4px] flex items-center justify-center cursor-pointer transition-colors hover:border-[#3E3E4E] shrink-0"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            <RefreshIconSvg />
          </button>

          <select
            aria-label="Driver Backend Selector"
            value={driverBackend}
            onChange={(e) =>
              setDriverBackend(e.target.value as "DirectShow" | "MSMF")
            }
            className="w-[96px] h-[28px] px-1.5 rounded-[4px] text-[11px] font-medium cursor-pointer focus:outline-none"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            <option value="DirectShow">DirectShow</option>
            <option value="MSMF">MSMF</option>
          </select>

          <button
            type="button"
            onClick={() => setShowDriverSheetModal(true)}
            className="w-[64px] h-[28px] rounded-[4px] text-[11px] font-semibold whitespace-nowrap shrink-0 cursor-pointer"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            DRV CFG
          </button>
        </div>

        {/* Center Telemetry Cluster (Technical Readout Strip) */}
        <div className="hidden lg:flex items-center gap-[6px] font-mono text-[10.5px] font-semibold tabular-nums shrink-0">
          <span
            className="px-2 py-1 rounded-[4px] whitespace-nowrap"
            style={{
              backgroundColor: "#14141A",
              border: "1px solid #262632",
              color: "#E5A93C",
            }}
          >
            {params.upscale_1080p ? "RES: 1920x1080 (HQ)" : "RES: 1280x720"}
          </span>

          <span
            className="px-2 py-1 rounded-[4px] whitespace-nowrap"
            style={{
              backgroundColor: "#14141A",
              border: "1px solid #262632",
              color: getFpsBadgeColor(liveFps),
            }}
          >
            FPS: {liveFps.toFixed(1)}
          </span>

          <span
            className="px-2 py-1 rounded-[4px] whitespace-nowrap"
            style={{
              backgroundColor: "#14141A",
              border: "1px solid #262632",
              color: "#E5A93C",
            }}
          >
            {params.manual_exposure_lock
              ? `EXP: ${params.hardware_exposure} (LOCKED)`
              : "EXP: AUTO"}
          </span>

          <span
            className="px-2 py-1 rounded-[4px] whitespace-nowrap"
            style={{
              backgroundColor: "#14141A",
              border: "1px solid #262632",
              color: "#E5A93C",
            }}
          >
            GAIN: {params.hardware_gain}
          </span>

          <span
            className="px-2 py-1 rounded-[4px] whitespace-nowrap"
            style={{
              backgroundColor: "#14141A",
              border: "1px solid #262632",
              color: "#E5A93C",
            }}
          >
            {params.auto_wb ? "WB: AUTO" : `WB: ${params.wb_kelvin}K`}
          </span>

          <span
            className="px-2 py-1 rounded-[4px] whitespace-nowrap"
            style={{
              backgroundColor: "#14141A",
              border: "1px solid #262632",
              color: "#E5A93C",
            }}
          >
            LUT: {shortLutBadge}
          </span>
        </div>

        {/* Right Cluster */}
        <div className="flex items-center gap-[8px] shrink-0">
          <button
            type="button"
            onClick={() => setShowRepoModal(true)}
            className="h-[28px] px-2 rounded-[4px] font-mono text-[10px] font-semibold whitespace-nowrap shrink-0 cursor-pointer"
            style={{
              backgroundColor: "#262118",
              border: "1px solid #E5A93C",
              color: "#E5A93C",
            }}
          >
            PY REPO ({repoFiles.length || 16})
          </button>

          <span
            aria-hidden="true"
            className="w-[10px] h-[10px] rounded-full shrink-0"
            style={{
              backgroundColor:
                isRecording && tallyBlinkOn ? "#E11D48" : "#3F3F46",
            }}
          />

          <span
            className="font-mono text-[14px] font-bold tabular-nums tracking-tight whitespace-nowrap shrink-0"
            style={{ color: "#F4F4F6" }}
          >
            {formatMasterTimecode(recordedFrames, 30)}
          </span>
        </div>
      </header>

      {/* =====================================================================
          MIDDLE WORKSPACE (Zone B + Zone C + Zone D)
      ===================================================================== */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* ZONE B — Left Dock Inspector: Hardware UVC & Optical ISP (320px) */}
        <aside
          aria-label="Hardware UVC and Optical ISP Inspector"
          className="w-[320px] h-full shrink-0 overflow-y-auto p-[12px] flex flex-col gap-[12px]"
          style={{
            backgroundColor: "#0E0E12",
            borderRight: "1px solid #22222B",
          }}
        >
          {/* Card 1: C270 30-FPS HARDWARE ENGINE */}
          <InspectorCard title="C270 30-FPS HARDWARE ENGINE">
            <ToggleSwitch
              label="30 FPS Low-Light Lock (Manual Exp)"
              checked={params.manual_exposure_lock}
              onChange={(v) => updateParam("manual_exposure_lock", v)}
            />
            <ToggleSwitch
              label="50Hz Powerline Anti-Flicker"
              checked={params.anti_flicker_50hz}
              onChange={(v) => updateParam("anti_flicker_50hz", v)}
            />
            <PrecisionSlider
              title="Hardware Exposure"
              min={-11}
              max={-2}
              defaultValue={-5}
              value={params.hardware_exposure}
              step={1}
              decimals={0}
              suffix=" EV"
              onChange={(v) => updateParam("hardware_exposure", v)}
            />
            <PrecisionSlider
              title="Sensor Gain (ISO)"
              min={0}
              max={255}
              defaultValue={110}
              value={params.hardware_gain}
              step={1}
              decimals={0}
              suffix=" ISO"
              onChange={(v) => updateParam("hardware_gain", v)}
            />
            <PrecisionSlider
              title="Backlight Comp"
              min={0}
              max={2}
              defaultValue={0}
              value={params.backlight_comp}
              step={1}
              decimals={0}
              onChange={(v) => updateParam("backlight_comp", v)}
            />
          </InspectorCard>

          {/* Card 2: SENSOR COLOR & WHITE BALANCE */}
          <InspectorCard title="SENSOR COLOR & WHITE BALANCE">
            <ToggleSwitch
              label="Auto White Balance"
              checked={params.auto_wb}
              onChange={(v) => updateParam("auto_wb", v)}
            />
            <PrecisionSlider
              title="Color Temp (Kelvin)"
              min={2800}
              max={7500}
              defaultValue={5000}
              value={params.wb_kelvin}
              step={100}
              decimals={0}
              suffix="K"
              onChange={(v) => updateParam("wb_kelvin", v)}
            />
            <PrecisionSlider
              title="Hardware Brightness"
              min={0}
              max={255}
              defaultValue={128}
              value={params.hardware_brightness}
              step={1}
              decimals={0}
              onChange={(v) => updateParam("hardware_brightness", v)}
            />
            <PrecisionSlider
              title="Hardware Contrast"
              min={0}
              max={255}
              defaultValue={135}
              value={params.hardware_contrast}
              step={1}
              decimals={0}
              onChange={(v) => updateParam("hardware_contrast", v)}
            />
            <PrecisionSlider
              title="Hardware Saturation"
              min={0}
              max={255}
              defaultValue={132}
              value={params.hardware_saturation}
              step={1}
              decimals={0}
              onChange={(v) => updateParam("hardware_saturation", v)}
            />
            <PrecisionSlider
              title="Hardware Sharpness"
              min={0}
              max={255}
              defaultValue={140}
              value={params.hardware_sharpness}
              step={1}
              decimals={0}
              onChange={(v) => updateParam("hardware_sharpness", v)}
            />
          </InspectorCard>

          {/* Card 3: OPTICAL ISP & SUPER-RESOLUTION */}
          <InspectorCard title="OPTICAL ISP & SUPER-RESOLUTION">
            <SegmentedBar
              options={["720p Native", "1080p Lanczos4 Master"]}
              activeIndex={params.upscale_1080p ? 1 : 0}
              onSelect={(idx) => updateParam("upscale_1080p", idx === 1)}
              height={30}
            />
            <PrecisionSlider
              title="Optical Clarity (Unsharp Mask)"
              min={0.0}
              max={3.0}
              defaultValue={0.8}
              value={params.optical_clarity}
              step={0.05}
              decimals={2}
              onChange={(v) => updateParam("optical_clarity", v)}
            />
            <PrecisionSlider
              title="Chroma/Luma Denoise"
              min={0.0}
              max={1.0}
              defaultValue={0.15}
              value={params.denoise_strength}
              step={0.05}
              decimals={2}
              onChange={(v) => updateParam("denoise_strength", v)}
            />
            <PrecisionSlider
              title="Edge Detail Preservation"
              min={0.1}
              max={2.0}
              defaultValue={1.0}
              value={params.edge_detail_radius}
              step={0.05}
              decimals={2}
              onChange={(v) => updateParam("edge_detail_radius", v)}
            />
          </InspectorCard>

          {/* Card 4: FLUID PTZ & GEOMETRY */}
          <InspectorCard title="FLUID PTZ & GEOMETRY">
            <PrecisionSlider
              title="Digital Optical Zoom"
              min={1.0}
              max={3.0}
              defaultValue={1.0}
              value={params.digital_zoom}
              step={0.02}
              decimals={2}
              suffix="x"
              onChange={(v) => updateParam("digital_zoom", v)}
            />
            <PrecisionSlider
              title="Pan X (Horizontal)"
              min={-1.0}
              max={1.0}
              defaultValue={0.0}
              value={params.pan_x}
              step={0.02}
              decimals={2}
              bipolar
              onChange={(v) => updateParam("pan_x", v)}
            />
            <PrecisionSlider
              title="Tilt Y (Vertical)"
              min={-1.0}
              max={1.0}
              defaultValue={0.0}
              value={params.tilt_y}
              step={0.02}
              decimals={2}
              bipolar
              onChange={(v) => updateParam("tilt_y", v)}
            />

            <div className="grid grid-cols-4 gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => updateParam("mirror_h", !params.mirror_h)}
                className="h-[30px] rounded-[4px] text-[10.5px] font-semibold whitespace-nowrap cursor-pointer"
                style={{
                  backgroundColor: params.mirror_h ? "#262118" : "#1C1C24",
                  border: params.mirror_h
                    ? "1px solid #E5A93C"
                    : "1px solid #2C2C38",
                  color: params.mirror_h ? "#E5A93C" : "#F4F4F6",
                }}
              >
                Mirror H
              </button>
              <button
                type="button"
                onClick={() => updateParam("flip_v", !params.flip_v)}
                className="h-[30px] rounded-[4px] text-[10.5px] font-semibold whitespace-nowrap cursor-pointer"
                style={{
                  backgroundColor: params.flip_v ? "#262118" : "#1C1C24",
                  border: params.flip_v
                    ? "1px solid #E5A93C"
                    : "1px solid #2C2C38",
                  color: params.flip_v ? "#E5A93C" : "#F4F4F6",
                }}
              >
                Flip V
              </button>
              <button
                type="button"
                onClick={() =>
                  updateParam("rotate_quadrant", (params.rotate_quadrant + 1) % 4)
                }
                className="h-[30px] rounded-[4px] text-[10.5px] font-semibold whitespace-nowrap cursor-pointer"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#F4F4F6",
                }}
              >
                Rotate 90°
              </button>
              <button
                type="button"
                onClick={() => {
                  updateParam("digital_zoom", 1.0);
                  updateParam("pan_x", 0.0);
                  updateParam("tilt_y", 0.0);
                  updateParam("rotate_quadrant", 0);
                }}
                className="h-[30px] rounded-[4px] text-[10.5px] font-semibold whitespace-nowrap cursor-pointer"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#F4F4F6",
                }}
              >
                Reset PTZ
              </button>
            </div>
          </InspectorCard>
        </aside>

        {/* ZONE C — Center Cinema Viewport & Interactive HUD */}
        <ViewportCanvas
          params={params}
          customCubeLut={customCubeLut}
          backdropImageElement={backdropImageEl}
          watermarkImageElement={watermarkImageEl}
          isRecording={isRecording}
          isVirtualCam={isVirtualCam}
          countdownValue={countdownValue}
          flashTriggerCounter={flashTriggerCounter}
          captureRequestCounter={captureRequestCounter}
          onFrameCaptured={handleFrameCaptured}
          onFpsUpdated={setLiveFps}
          onPtzDragged={(z, px, py) => {
            updateParam("digital_zoom", z);
            updateParam("pan_x", px);
            updateParam("tilt_y", py);
          }}
          onPtzReset={() => {
            updateParam("digital_zoom", 1.0);
            updateParam("pan_x", 0.0);
            updateParam("tilt_y", 0.0);
          }}
        />

        {/* ZONE D — Right Dock Inspector: Color Grading, AI Studio & Broadcast Overlays (340px) */}
        <aside
          aria-label="Color Grading, AI Studio, and Broadcast Overlays Inspector"
          className="w-[340px] h-full shrink-0 flex flex-col"
          style={{
            backgroundColor: "#0E0E12",
            borderLeft: "1px solid #22222B",
          }}
        >
          {/* Top 3-Tab Segmented Bar (Height: 36px) */}
          <div
            className="h-[36px] px-2 flex items-center shrink-0"
            style={{
              backgroundColor: "#0A0A0D",
              borderBottom: "1px solid #22222B",
            }}
          >
            <SegmentedBar
              options={["COLOR & LUT", "AI STUDIO", "OVERLAYS"]}
              activeIndex={rightTabIndex}
              onSelect={setRightTabIndex}
              height={28}
            />
          </div>

          <div className="flex-1 overflow-y-auto p-[12px] flex flex-col gap-[12px]">
            {rightTabIndex === 0 && (
              <>
                {/* TAB 1 - Card 1: FILM LOOKS & 3D LUT ENGINE */}
                <InspectorCard title="FILM LOOKS & 3D LUT ENGINE">
                  <div className="grid grid-cols-2 gap-1.5">
                    {FILM_LOOK_NAMES.map((look) => {
                      const active = params.film_look === look;
                      return (
                        <button
                          key={look}
                          type="button"
                          onClick={() => updateParam("film_look", look)}
                          className="h-[34px] px-2.5 rounded-[4px] flex items-center gap-2 text-[11px] font-semibold cursor-pointer transition-colors"
                          style={{
                            backgroundColor: active ? "#262118" : "#1C1C24",
                            border: active
                              ? "1px solid #E5A93C"
                              : "1px solid #2C2C38",
                            color: active ? "#E5A93C" : "#F4F4F6",
                          }}
                        >
                          <span
                            className="w-[6px] h-[6px] rounded-full shrink-0"
                            style={{
                              backgroundColor: active
                                ? "#E5A93C"
                                : "transparent",
                            }}
                          />
                          <span className="truncate">{look}</span>
                        </button>
                      );
                    })}
                  </div>

                  <div className="flex items-center gap-1.5 pt-1">
                    <button
                      type="button"
                      onClick={() => cubeInputRef.current?.click()}
                      className="flex-1 h-[28px] px-2 rounded-[4px] text-[11px] font-semibold truncate cursor-pointer"
                      style={{
                        backgroundColor: "#1C1C24",
                        border: "1px solid #2C2C38",
                        color: "#F4F4F6",
                      }}
                    >
                      {params.custom_cube_name
                        ? `CUBE: ${params.custom_cube_name}`
                        : "Load Custom .CUBE LUT..."}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setCustomCubeLut(null);
                        updateParam("custom_cube_name", "");
                      }}
                      className="w-[74px] h-[28px] rounded-[4px] text-[11px] font-semibold shrink-0 cursor-pointer"
                      style={{
                        backgroundColor: "#1C1C24",
                        border: "1px solid #2C2C38",
                        color: "#9CA3AF",
                      }}
                    >
                      Clear LUT
                    </button>
                  </div>

                  <PrecisionSlider
                    title="LUT Intensity / Mix"
                    min={0}
                    max={100}
                    defaultValue={100}
                    value={params.lut_intensity}
                    step={1}
                    decimals={0}
                    suffix="%"
                    onChange={(v) => updateParam("lut_intensity", v)}
                  />
                </InspectorCard>

                {/* TAB 1 - Card 2: PRIMARY COLOR WHEELS / GRADING */}
                <InspectorCard title="PRIMARY COLOR WHEELS / GRADING">
                  <PrecisionSlider
                    title="Color Temp Shift"
                    min={-100}
                    max={100}
                    defaultValue={0}
                    value={params.temp_shift}
                    step={1}
                    decimals={0}
                    bipolar
                    onChange={(v) => updateParam("temp_shift", v)}
                  />
                  <PrecisionSlider
                    title="Tint (Green / Magenta)"
                    min={-100}
                    max={100}
                    defaultValue={0}
                    value={params.tint_shift}
                    step={1}
                    decimals={0}
                    bipolar
                    onChange={(v) => updateParam("tint_shift", v)}
                  />
                  <PrecisionSlider
                    title="Shadows (Lift)"
                    min={-50}
                    max={50}
                    defaultValue={0}
                    value={params.shadows_lift}
                    step={1}
                    decimals={0}
                    bipolar
                    onChange={(v) => updateParam("shadows_lift", v)}
                  />
                  <PrecisionSlider
                    title="Midtones (Gamma)"
                    min={0.5}
                    max={2.0}
                    defaultValue={1.0}
                    value={params.midtones_gamma}
                    step={0.02}
                    decimals={2}
                    onChange={(v) => updateParam("midtones_gamma", v)}
                  />
                  <PrecisionSlider
                    title="Highlights (Gain)"
                    min={-50}
                    max={50}
                    defaultValue={0}
                    value={params.highlights_gain}
                    step={1}
                    decimals={0}
                    bipolar
                    onChange={(v) => updateParam("highlights_gain", v)}
                  />
                  <PrecisionSlider
                    title="S-Curve Contrast"
                    min={0.0}
                    max={1.0}
                    defaultValue={0.15}
                    value={params.scurve_contrast}
                    step={0.02}
                    decimals={2}
                    onChange={(v) => updateParam("scurve_contrast", v)}
                  />
                  <PrecisionSlider
                    title="Vibrance (Smart Sat)"
                    min={-100}
                    max={100}
                    defaultValue={15}
                    value={params.vibrance}
                    step={1}
                    decimals={0}
                    bipolar
                    onChange={(v) => updateParam("vibrance", v)}
                  />
                </InspectorCard>

                {/* TAB 1 - Card 3: OPTICAL TEXTURE & LENS */}
                <InspectorCard title="OPTICAL TEXTURE & LENS">
                  <PrecisionSlider
                    title="Optical Vignette"
                    min={0.0}
                    max={1.0}
                    defaultValue={0.15}
                    value={params.optical_vignette}
                    step={0.02}
                    decimals={2}
                    onChange={(v) => updateParam("optical_vignette", v)}
                  />
                  <PrecisionSlider
                    title="Organic Film Grain"
                    min={0.0}
                    max={1.0}
                    defaultValue={0.0}
                    value={params.film_grain}
                    step={0.02}
                    decimals={2}
                    onChange={(v) => updateParam("film_grain", v)}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      updateParam("lut_intensity", 100);
                      updateParam("temp_shift", 0);
                      updateParam("tint_shift", 0);
                      updateParam("shadows_lift", 0);
                      updateParam("midtones_gamma", 1.0);
                      updateParam("highlights_gain", 0);
                      updateParam("scurve_contrast", 0.15);
                      updateParam("vibrance", 15);
                      updateParam("optical_vignette", 0.15);
                      updateParam("film_grain", 0.0);
                    }}
                    className="w-full h-[30px] rounded-[4px] text-[11px] font-semibold cursor-pointer"
                    style={{
                      backgroundColor: "#1C1C24",
                      border: "1px solid #2C2C38",
                      color: "#F4F4F6",
                    }}
                  >
                    Reset Color Grade
                  </button>
                </InspectorCard>
              </>
            )}

            {rightTabIndex === 1 && (
              <>
                {/* TAB 2 - Card 1: BACKGROUND & STUDIO LIGHTING MODE */}
                <InspectorCard title="BACKGROUND & STUDIO LIGHTING MODE">
                  <select
                    aria-label="Background and Studio Lighting Mode"
                    value={params.ai_mode}
                    onChange={(e) =>
                      updateParam("ai_mode", e.target.value as AIStudioMode)
                    }
                    className="w-full h-[30px] px-2 rounded-[4px] text-[11px] font-medium cursor-pointer focus:outline-none"
                    style={{
                      backgroundColor: "#1C1C24",
                      border: "1px solid #2C2C38",
                      color: "#F4F4F6",
                    }}
                  >
                    <option value="Off (Natural Scene)">
                      Off (Natural Scene)
                    </option>
                    <option value="Studio Spotlight (Dim Background)">
                      Studio Spotlight (Dim Background)
                    </option>
                    <option value="Optical Bokeh Blur (DSLR Portrait)">
                      Optical Bokeh Blur (DSLR Portrait)
                    </option>
                    <option value="Custom Studio Backdrop">
                      Custom Studio Backdrop
                    </option>
                  </select>

                  <PrecisionSlider
                    title="Spotlight Dimming %"
                    min={10}
                    max={85}
                    defaultValue={45}
                    value={params.spotlight_dim_pct}
                    step={1}
                    decimals={0}
                    suffix="%"
                    onChange={(v) => updateParam("spotlight_dim_pct", v)}
                  />
                  <PrecisionSlider
                    title="Bokeh Blur Radius"
                    min={5}
                    max={65}
                    defaultValue={25}
                    value={params.bokeh_blur_radius}
                    step={2}
                    decimals={0}
                    onChange={(v) => updateParam("bokeh_blur_radius", v)}
                  />
                  <PrecisionSlider
                    title="Edge Feather / Spill Suppression"
                    min={1}
                    max={25}
                    defaultValue={7}
                    value={params.edge_feather}
                    step={1}
                    decimals={0}
                    onChange={(v) => updateParam("edge_feather", v)}
                  />

                  <div className="grid grid-cols-4 gap-1.5 pt-1">
                    {[
                      { name: "Obsidian", hex: "#121216" },
                      { name: "Slate", hex: "#1E293B" },
                      { name: "Plum", hex: "#2E1035" },
                      { name: "Forest", hex: "#0F291E" },
                    ].map((sw) => (
                      <button
                        key={sw.name}
                        type="button"
                        onClick={() => {
                          setBackdropImageEl(null);
                          updateParam("backdrop_color_hex", sw.hex);
                          updateParam("ai_mode", "Custom Studio Backdrop");
                        }}
                        className="h-[26px] rounded-[4px] text-[10px] font-semibold cursor-pointer"
                        style={{
                          backgroundColor: sw.hex,
                          border:
                            params.backdrop_color_hex === sw.hex
                              ? "1px solid #E5A93C"
                              : "1px solid #3E3E4E",
                          color: "#F4F4F6",
                        }}
                      >
                        {sw.name}
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      type="button"
                      onClick={() => colorPickerInputRef.current?.click()}
                      className="h-[28px] rounded-[4px] text-[10.5px] font-semibold cursor-pointer"
                      style={{
                        backgroundColor: "#1C1C24",
                        border: "1px solid #2C2C38",
                        color: "#F4F4F6",
                      }}
                    >
                      Pick Custom Color...
                    </button>
                    <button
                      type="button"
                      onClick={() => backdropInputRef.current?.click()}
                      className="h-[28px] rounded-[4px] text-[10.5px] font-semibold cursor-pointer"
                      style={{
                        backgroundColor: "#1C1C24",
                        border: "1px solid #2C2C38",
                        color: "#F4F4F6",
                      }}
                    >
                      Load Backdrop Image...
                    </button>
                  </div>
                </InspectorCard>

                {/* TAB 2 - Card 2: AI CENTER STAGE (AUTO-FRAMING) */}
                <InspectorCard title="AI CENTER STAGE (AUTO-FRAMING)">
                  <ToggleSwitch
                    label="AI Face Auto-Framing (Center Stage)"
                    checked={params.auto_framing}
                    onChange={(v) => updateParam("auto_framing", v)}
                  />
                  <PrecisionSlider
                    title="Subject Target Zoom"
                    min={1.15}
                    max={2.2}
                    defaultValue={1.35}
                    value={params.subject_target_zoom}
                    step={0.05}
                    decimals={2}
                    suffix="x"
                    onChange={(v) => updateParam("subject_target_zoom", v)}
                  />
                  <PrecisionSlider
                    title="Gimbal Damping (Smoothness)"
                    min={0.02}
                    max={0.3}
                    defaultValue={0.08}
                    value={params.gimbal_damping}
                    step={0.01}
                    decimals={2}
                    onChange={(v) => updateParam("gimbal_damping", v)}
                  />
                </InspectorCard>

                {/* TAB 2 - Card 3: PORTRAIT SKIN RETOUCH */}
                <InspectorCard title="PORTRAIT SKIN RETOUCH">
                  <PrecisionSlider
                    title="Frequency Skin Smoothing"
                    min={0.0}
                    max={1.0}
                    defaultValue={0.0}
                    value={params.skin_smoothing}
                    step={0.05}
                    decimals={2}
                    onChange={(v) => updateParam("skin_smoothing", v)}
                  />
                </InspectorCard>
              </>
            )}

            {rightTabIndex === 2 && (
              <>
                {/* TAB 3 - Card 1: VIEWPORT TELEMETRY & GUIDES */}
                <InspectorCard title="VIEWPORT TELEMETRY & GUIDES">
                  <ToggleSwitch
                    label="Show Live Histogram"
                    checked={params.show_histogram}
                    onChange={(v) => updateParam("show_histogram", v)}
                  />
                  <ToggleSwitch
                    label="Show Audio VU Meter"
                    checked={params.show_vu_meter}
                    onChange={(v) => updateParam("show_vu_meter", v)}
                  />
                  <ToggleSwitch
                    label="Rule of Thirds Grid"
                    checked={params.guide_thirds}
                    onChange={(v) => updateParam("guide_thirds", v)}
                  />
                  <ToggleSwitch
                    label="Golden Ratio Grid"
                    checked={params.guide_golden}
                    onChange={(v) => updateParam("guide_golden", v)}
                  />
                  <ToggleSwitch
                    label="Center Crosshair & Safe Area"
                    checked={params.guide_crosshair_safe}
                    onChange={(v) => updateParam("guide_crosshair_safe", v)}
                  />
                  <ToggleSwitch
                    label="2.35:1 Anamorphic Crop Bars"
                    checked={params.guide_anamorphic}
                    onChange={(v) => updateParam("guide_anamorphic", v)}
                  />
                  <ToggleSwitch
                    label="9:16 Vertical Reel Guide"
                    checked={params.guide_vertical_reel}
                    onChange={(v) => updateParam("guide_vertical_reel", v)}
                  />
                </InspectorCard>

                {/* TAB 3 - Card 2: LOWER THIRD BROADCAST GRAPHIC */}
                <InspectorCard title="LOWER THIRD BROADCAST GRAPHIC">
                  <ToggleSwitch
                    label="Show Lower Third Card"
                    checked={params.show_lower_third}
                    onChange={(v) => updateParam("show_lower_third", v)}
                  />
                  <input
                    type="text"
                    aria-label="Presenter Name"
                    placeholder="Presenter Name"
                    value={params.lower_third_name}
                    onChange={(e) =>
                      updateParam("lower_third_name", e.target.value)
                    }
                    className="w-full h-[28px] px-2 rounded-[4px] text-[11px] focus:outline-none"
                    style={{
                      backgroundColor: "#1C1C24",
                      border: "1px solid #2C2C38",
                      color: "#F4F4F6",
                    }}
                  />
                  <input
                    type="text"
                    aria-label="Title or Role"
                    placeholder="Title / Role"
                    value={params.lower_third_role}
                    onChange={(e) =>
                      updateParam("lower_third_role", e.target.value)
                    }
                    className="w-full h-[28px] px-2 rounded-[4px] text-[11px] focus:outline-none"
                    style={{
                      backgroundColor: "#1C1C24",
                      border: "1px solid #2C2C38",
                      color: "#F4F4F6",
                    }}
                  />
                  <select
                    aria-label="Lower Third Accent Style"
                    value={params.lower_third_accent}
                    onChange={(e) =>
                      updateParam("lower_third_accent", e.target.value)
                    }
                    className="w-full h-[28px] px-2 rounded-[4px] text-[11px] cursor-pointer focus:outline-none"
                    style={{
                      backgroundColor: "#1C1C24",
                      border: "1px solid #2C2C38",
                      color: "#F4F4F6",
                    }}
                  >
                    <option value="Leica Amber (#E5A93C)">
                      Leica Amber (#E5A93C)
                    </option>
                    <option value="Minimal Monochrome (#F4F4F6)">
                      Minimal Monochrome (#F4F4F6)
                    </option>
                    <option value="Crimson Broadcast (#E11D48)">
                      Crimson Broadcast (#E11D48)
                    </option>
                  </select>
                </InspectorCard>

                {/* TAB 3 - Card 3: STUDIO WATERMARK & TIMECODE */}
                <InspectorCard title="STUDIO WATERMARK & TIMECODE">
                  <ToggleSwitch
                    label="Show Custom PNG Logo"
                    checked={params.show_watermark}
                    onChange={(v) => updateParam("show_watermark", v)}
                  />
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => watermarkInputRef.current?.click()}
                      className="flex-1 h-[28px] px-2 rounded-[4px] text-[11px] font-semibold cursor-pointer"
                      style={{
                        backgroundColor: "#1C1C24",
                        border: "1px solid #2C2C38",
                        color: "#F4F4F6",
                      }}
                    >
                      Select PNG Logo...
                    </button>
                    <select
                      aria-label="Watermark Corner Position"
                      value={params.watermark_position}
                      onChange={(e) =>
                        updateParam(
                          "watermark_position",
                          e.target.value as StudioParams["watermark_position"]
                        )
                      }
                      className="w-[110px] h-[28px] px-1.5 rounded-[4px] text-[11px] cursor-pointer focus:outline-none"
                      style={{
                        backgroundColor: "#1C1C24",
                        border: "1px solid #2C2C38",
                        color: "#F4F4F6",
                      }}
                    >
                      <option value="Top-Right">Top-Right</option>
                      <option value="Top-Left">Top-Left</option>
                      <option value="Bottom-Right">Bottom-Right</option>
                      <option value="Bottom-Left">Bottom-Left</option>
                    </select>
                  </div>
                  <PrecisionSlider
                    title="Logo Opacity"
                    min={10}
                    max={100}
                    defaultValue={80}
                    value={params.watermark_opacity}
                    step={1}
                    decimals={0}
                    suffix="%"
                    onChange={(v) => updateParam("watermark_opacity", v)}
                  />
                  <ToggleSwitch
                    label="Burn-in Cinema Timecode & Date"
                    checked={params.burn_in_timecode}
                    onChange={(v) => updateParam("burn_in_timecode", v)}
                  />
                </InspectorCard>
              </>
            )}
          </div>
        </aside>
      </div>

      {/* =====================================================================
          ZONE E — Bottom Transport, Capture & Preset Deck (Fixed Height: 76px)
      ===================================================================== */}
      <footer
        className="h-[76px] px-[18px] flex items-center justify-between gap-4 shrink-0"
        style={{
          backgroundColor: "#0A0A0D",
          borderTop: "1px solid #22222B",
        }}
      >
        {/* Left Cluster (Preset Management) */}
        <div className="flex items-center gap-2 shrink-0">
          <span
            className="text-[10px] font-bold uppercase tracking-[1.2px]"
            style={{ color: "#71717A" }}
          >
            PRESET:
          </span>

          {savingPresetMode ? (
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                aria-label="New Preset Name"
                value={newPresetTitle}
                onChange={(e) => setNewPresetTitle(e.target.value)}
                className="w-[150px] h-[32px] px-2 rounded-[4px] text-[11px] focus:outline-none"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #E5A93C",
                  color: "#F4F4F6",
                }}
              />
              <button
                type="button"
                onClick={handleSaveCustomPreset}
                className="h-[32px] px-2.5 rounded-[4px] text-[11px] font-semibold cursor-pointer"
                style={{
                  backgroundColor: "#262118",
                  border: "1px solid #E5A93C",
                  color: "#E5A93C",
                }}
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={() => setSavingPresetMode(false)}
                className="h-[32px] px-2 rounded-[4px] text-[11px] font-semibold cursor-pointer"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#9CA3AF",
                }}
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <select
                aria-label="Studio Preset Selector"
                value={activePresetName}
                onChange={(e) => handleSelectPreset(e.target.value)}
                className="w-[200px] h-[32px] px-2 rounded-[4px] text-[11px] font-medium cursor-pointer focus:outline-none"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#F4F4F6",
                }}
              >
                {presetNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={() => setSavingPresetMode(true)}
                className="w-[58px] h-[32px] rounded-[4px] text-[11px] font-semibold cursor-pointer"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#F4F4F6",
                }}
              >
                Save
              </button>

              <button
                type="button"
                onClick={handleDeletePreset}
                className="w-[58px] h-[32px] rounded-[4px] text-[11px] font-semibold cursor-pointer"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#F4F4F6",
                }}
              >
                Delete
              </button>

              <button
                type="button"
                onClick={handleResetAll}
                className="w-[74px] h-[32px] rounded-[4px] text-[11px] font-semibold cursor-pointer"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#F4F4F6",
                }}
              >
                Reset All
              </button>
            </>
          )}
        </div>

        {/* Center Cluster (Tactile Camera Transport Controls) */}
        <div className="flex items-center gap-2.5 shrink-0">
          <select
            aria-label="Shutter Countdown Timer"
            value={timerMode}
            onChange={(e) => setTimerMode(e.target.value)}
            className="w-[100px] h-[32px] px-2 rounded-[4px] text-[11px] font-medium cursor-pointer focus:outline-none"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            <option value="Timer: Off">Timer: Off</option>
            <option value="3s Timer">3s Timer</option>
            <option value="5s Timer">5s Timer</option>
            <option value="10s Timer">10s Timer</option>
          </select>

          <button
            type="button"
            onClick={() => setFlashEnabled(!flashEnabled)}
            className="w-[68px] h-[32px] rounded-[4px] text-[11px] font-semibold cursor-pointer transition-colors"
            style={{
              backgroundColor: flashEnabled ? "#262118" : "#1C1C24",
              border: flashEnabled
                ? "1px solid #E5A93C"
                : "1px solid #2C2C38",
              color: flashEnabled ? "#E5A93C" : "#F4F4F6",
            }}
          >
            FLASH
          </button>

          <ShutterReleaseButton onClick={handleShutterRelease} />

          <CinemaRecordButton
            recording={isRecording}
            onClick={handleToggleRecord}
          />

          <PauseRecordButton
            enabled={isRecording}
            paused={isPausedRecording}
            onClick={() => setIsPausedRecording(!isPausedRecording)}
          />

          <button
            type="button"
            onClick={handleBurst3x}
            className="w-[78px] h-[32px] rounded-[4px] text-[11px] font-semibold whitespace-nowrap cursor-pointer"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            BURST 3X
          </button>
        </div>

        {/* Right Cluster (Output & Routing) */}
        <div className="flex items-center gap-2.5 shrink-0">
          <select
            aria-label="Snapshot Format"
            value={snapshotFormat}
            onChange={(e) => setSnapshotFormat(e.target.value)}
            className="w-[120px] h-[32px] px-2 rounded-[4px] text-[11px] font-medium cursor-pointer focus:outline-none"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            <option value="PNG Lossless">PNG Lossless</option>
            <option value="JPG 100%">JPG 100%</option>
          </select>

          <button
            type="button"
            onClick={() => {
              const next = !isVirtualCam;
              setIsVirtualCam(next);
              setStatusBanner(
                next
                  ? "PYVIRTUALCAM BROADCAST ACTIVE (OBS VIRTUALCAM 30FPS)"
                  : "VIRTUAL CAMERA BROADCAST STOPPED"
              );
            }}
            className="w-[150px] h-[34px] rounded-[4px] text-[11px] font-semibold whitespace-nowrap cursor-pointer transition-colors"
            style={{
              backgroundColor: isVirtualCam ? "#0F2922" : "#1C1C24",
              border: isVirtualCam
                ? "1px solid #10B981"
                : "1px solid #2C2C38",
              color: isVirtualCam ? "#10B981" : "#F4F4F6",
            }}
          >
            {isVirtualCam ? "VIRTUAL CAM: LIVE" : "VIRTUAL CAM: OFF"}
          </button>

          <button
            type="button"
            onClick={() => setShowGalleryModal(true)}
            className="w-[115px] h-[34px] rounded-[4px] text-[11px] font-semibold whitespace-nowrap cursor-pointer"
            style={{
              backgroundColor: "#1C1C24",
              border: "1px solid #2C2C38",
              color: "#F4F4F6",
            }}
          >
            OPEN GALLERY {capturedItems.length > 0 ? `(${capturedItems.length})` : ""}
          </button>
        </div>
      </footer>

      {/* DirectShow Native Driver Property Sheet Modal (`DRV CFG`) */}
      {showDriverSheetModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="DirectShow UVC Hardware Register Sheet"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(7, 7, 9, 0.82)" }}
        >
          <div
            className="w-full max-w-[460px] rounded-[6px] p-4 flex flex-col gap-3"
            style={{
              backgroundColor: "#15151B",
              border: "1px solid #2C2C38",
            }}
          >
            <div className="flex items-center justify-between border-b border-[#22222B] pb-2">
              <span className="text-[11px] font-bold tracking-[1.2px] text-[#F4F4F6]">
                DIRECTSHOW UVC HARDWARE REGISTER SHEET (CAP_PROP_SETTINGS)
              </span>
              <button
                type="button"
                onClick={() => setShowDriverSheetModal(false)}
                className="px-2 py-0.5 rounded-[4px] text-[10px] font-semibold cursor-pointer bg-[#1C1C24] border border-[#2C2C38]"
              >
                CLOSE
              </button>
            </div>
            <div className="font-mono text-[11px] text-[#9CA3AF] flex flex-col gap-1.5">
              <div>DEVICE: {selectedDevice}</div>
              <div>BACKEND: cv2.CAP_{driverBackend === "DirectShow" ? "DSHOW" : "MSMF"} (MJPG FourCC)</div>
              <div>
                CAP_PROP_AUTO_EXPOSURE:{" "}
                <span className="text-[#E5A93C]">
                  {params.manual_exposure_lock ? "0.25 (Manual Lock)" : "0.75 (Auto)"}
                </span>
              </div>
              <div>
                CAP_PROP_EXPOSURE: <span className="text-[#E5A93C]">{params.hardware_exposure} EV</span>
              </div>
              <div>
                CAP_PROP_GAIN: <span className="text-[#E5A93C]">{params.hardware_gain} ISO</span>
              </div>
              <div>
                POWERLINE FREQUENCY (REG 39):{" "}
                <span className="text-[#10B981]">
                  {params.anti_flicker_50hz ? "50 Hz Anti-Flicker" : "60 Hz"}
                </span>
              </div>
              <div className="pt-1 text-[#71717A]">
                STATUS: {statusBanner}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Native Python Repository Inspector Modal */}
      <PythonRepoModal
        open={showRepoModal}
        onClose={() => setShowRepoModal(false)}
        repoFiles={repoFiles}
      />

      {/* Studio Media Gallery Modal */}
      <StudioGalleryModal
        open={showGalleryModal}
        onClose={() => setShowGalleryModal(false)}
        captures={capturedItems}
        onClearGallery={() => setCapturedItems([])}
      />
    </div>
  );
}
