import React, { useState, useCallback, useEffect } from 'react';
import {
  DEFAULT_STUDIO_PARAMS,
  FACTORY_PRESETS,
  STUDIO_LOOK_NAMES,
  StudioLookName,
  BackgroundMode,
  StudioParams,
} from './utils/ispMath';
import { ViewportCanvas } from './components/ViewportCanvas';
import { PythonRepoModal, RepoFileEntry } from './components/PythonRepoModal';

type SidebarTab = 'light' | 'color' | 'frame' | 'studio';

interface CapturedItem {
  id: string;
  timestamp: string;
  dataUrl: string;
  look: string;
  resolution: string;
}

export default function App() {
  const [params, setParams] = useState<StudioParams>(DEFAULT_STUDIO_PARAMS);
  const [activeTab, setActiveTab] = useState<SidebarTab>('light');
  const [selectedDevice, setSelectedDevice] = useState<string>(
    '0: Logitech HD Webcam C270 (DirectShow)'
  );
  const [useLiveWebcam, setUseLiveWebcam] = useState<boolean>(false);

  // Capture & Recording state
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingSec, setRecordingSec] = useState<number>(0);
  const [countdownVal, setCountdownVal] = useState<number>(0);
  const [flashActive, setFlashActive] = useState<boolean>(false);
  const [capturedGallery, setCapturedGallery] = useState<CapturedItem[]>([]);
  const [galleryModalOpen, setGalleryModalOpen] = useState<boolean>(false);
  const [repoModalOpen, setRepoModalOpen] = useState<boolean>(false);
  const [repoFiles, setRepoFiles] = useState<RepoFileEntry[]>([]);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  useEffect(() => {
    if (repoModalOpen && repoFiles.length === 0) {
      fetch('/api/repo-files')
        .then((r) => r.json())
        .then((data) => {
          if (data && Array.isArray(data.files)) {
            setRepoFiles(data.files);
          }
        })
        .catch(() => {});
    }
  }, [repoModalOpen, repoFiles.length]);

  const [telemetry, setTelemetry] = useState({
    fps: 30.0,
    processMs: 1.1,
    resolution: '720p HD',
    webcamConnected: false,
  });

  const [captureGetter, setCaptureGetter] = useState<(() => string | null) | null>(
    null
  );

  const handleCaptureGetterReady = useCallback((getter: () => string | null) => {
    setCaptureGetter(() => getter);
  }, []);

  const showNotice = useCallback((msg: string) => {
    setStatusNotice(msg);
    setTimeout(() => {
      setStatusNotice((prev) => (prev === msg ? null : prev));
    }, 2600);
  }, []);

  // Recording timer
  useEffect(() => {
    if (!isRecording) {
      setRecordingSec(0);
      return;
    }
    const timer = setInterval(() => {
      setRecordingSec((s) => s + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isRecording]);

  const updateParam = <K extends keyof StudioParams>(
    key: K,
    val: StudioParams[K]
  ) => {
    setParams((prev) => ({
      ...prev,
      [key]: val,
    }));
  };

  const handleApplyPreset = (presetName: string) => {
    const preset = FACTORY_PRESETS[presetName];
    if (!preset) return;
    setParams((prev) => ({
      ...DEFAULT_STUDIO_PARAMS,
      ...preset,
      active_preset_name: presetName,
      virtual_cam_active: prev.virtual_cam_active,
    }));
    showNotice(`Preset applied: ${presetName}`);
  };

  const handleResetAll = () => {
    setParams({
      ...DEFAULT_STUDIO_PARAMS,
      virtual_cam_active: false,
    });
    showNotice('Reset to 100% Pure Sensor Passthrough (30.0 FPS)');
  };

  const executeShutterCapture = useCallback(() => {
    if (params.screen_flash) {
      setFlashActive(true);
      setTimeout(() => setFlashActive(false), 180);
    }
    setTimeout(() => {
      if (captureGetter) {
        const dataUrl = captureGetter();
        if (dataUrl) {
          const item: CapturedItem = {
            id: `IMG_${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            dataUrl,
            look: params.pure_view_bypass ? 'Pure View' : params.active_lut,
            resolution: params.upscale_1080p ? '1920x1080' : '1280x720',
          };
          setCapturedGallery((prev) => [item, ...prev]);
          showNotice(`Saved still frame (${item.resolution})`);
        }
      }
    }, 60);
  }, [
    captureGetter,
    params.screen_flash,
    params.pure_view_bypass,
    params.active_lut,
    params.upscale_1080p,
    showNotice,
  ]);

  const handleTriggerPhoto = () => {
    if (countdownVal > 0) return;
    if (params.timer_sec === 0) {
      executeShutterCapture();
    } else {
      let rem = params.timer_sec;
      setCountdownVal(rem);
      const interval = setInterval(() => {
        rem -= 1;
        if (rem <= 0) {
          clearInterval(interval);
          setCountdownVal(0);
          executeShutterCapture();
        } else {
          setCountdownVal(rem);
        }
      }, 1000);
    }
  };

  const formatRecordTimer = (sec: number) => {
    const m = Math.floor(sec / 60)
      .toString()
      .padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `REC ${m}:${s}`;
  };

  return (
    <div
      className="w-screen h-screen flex flex-col overflow-hidden select-none"
      style={{
        backgroundColor: '#09090B',
        color: '#F4F4F5',
        fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
      }}
    >
      {/* 1. MINIMAL TOP HEADER BAR (52px height, #0D0D10) */}
      <header
        className="h-[52px] shrink-0 px-4 flex items-center justify-between"
        style={{
          backgroundColor: '#0D0D10',
          borderBottom: '1px solid #22222A',
        }}
      >
        {/* Left Group: Lens Icon + Title + Camera Selector (240px) + Driver Settings (115px) */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-2 pr-1">
            <svg
              width="20"
              height="20"
              viewBox="0 0 22 22"
              fill="none"
              className="shrink-0"
            >
              <circle
                cx="11"
                cy="11"
                r="8.5"
                stroke="#E5A93C"
                strokeWidth="1.6"
              />
              <circle
                cx="11"
                cy="11"
                r="3.8"
                stroke="#F4F4F5"
                strokeWidth="1.2"
              />
            </svg>
            <span className="text-[14px] font-bold tracking-[0.4px] text-[#F4F4F5] whitespace-nowrap">
              Optix Studio
            </span>
          </div>

          <select
            aria-label="Camera Device Selector"
            value={selectedDevice}
            onChange={(e) => {
              const val = e.target.value;
              setSelectedDevice(val);
              setUseLiveWebcam(val.includes('Browser WebRTC'));
            }}
            className="w-[240px] h-[32px] px-2.5 text-[12px] font-medium rounded-[6px] outline-none transition-colors cursor-pointer"
            style={{
              backgroundColor: '#1E1E26',
              border: '1px solid #2E2E3A',
              color: '#F4F4F5',
            }}
          >
            <option value="0: Logitech HD Webcam C270 (DirectShow)">
              0: Logitech HD Webcam C270 (DirectShow)
            </option>
            <option value="1: Live Browser WebRTC Camera">
              1: Live Browser WebRTC Camera
            </option>
          </select>

          <button
            type="button"
            onClick={() =>
              showNotice(
                'Opened Windows DirectShow UVC Hardware Driver Dialog (CAP_PROP_SETTINGS)'
              )
            }
            className="w-[115px] h-[32px] px-2.5 text-[12px] font-medium rounded-[6px] transition-colors cursor-pointer whitespace-nowrap"
            style={{
              backgroundColor: '#1E1E26',
              border: '1px solid #2E2E3A',
              color: '#F4F4F5',
            }}
          >
            Driver Settings
          </button>
        </div>

        {/* Center Status Pill (160px wide): Live Resolution & FPS */}
        <div
          className="w-[160px] h-[28px] px-3 rounded-[14px] flex items-center justify-center gap-2 shrink-0"
          style={{
            backgroundColor: '#14141A',
            border: '1px solid #262630',
          }}
        >
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ backgroundColor: '#10B981' }}
          />
          <span
            className="text-[11px] font-semibold whitespace-nowrap"
            style={{
              color: '#10B981',
              fontFamily: '"JetBrains Mono", Consolas, monospace',
            }}
          >
            {telemetry.resolution} &nbsp;|&nbsp; {telemetry.fps.toFixed(1)} FPS
          </span>
        </div>

        {/* Right Group: Pure View (Bypass) (140px) + Reset All (90px) + Gallery (90px) + Python Repo button */}
        <div className="flex items-center gap-2">
          {statusNotice && (
            <span className="text-[11px] text-[#E5A93C] mr-1 hidden xl:inline whitespace-nowrap">
              {statusNotice}
            </span>
          )}

          <button
            type="button"
            onClick={() =>
              updateParam('pure_view_bypass', !params.pure_view_bypass)
            }
            className="w-[140px] h-[32px] px-2.5 text-[12px] font-semibold rounded-[6px] transition-colors cursor-pointer whitespace-nowrap"
            style={{
              backgroundColor: params.pure_view_bypass
                ? 'rgba(229, 169, 60, 0.16)'
                : '#1E1E26',
              border: params.pure_view_bypass
                ? '1px solid #E5A93C'
                : '1px solid #2E2E3A',
              color: params.pure_view_bypass ? '#E5A93C' : '#F4F4F5',
            }}
          >
            Pure View (Bypass)
          </button>

          <button
            type="button"
            onClick={handleResetAll}
            className="w-[90px] h-[32px] px-2.5 text-[12px] font-medium rounded-[6px] transition-colors cursor-pointer whitespace-nowrap"
            style={{
              backgroundColor: '#1E1E26',
              border: '1px solid #2E2E3A',
              color: '#F4F4F5',
            }}
          >
            Reset All
          </button>

          <button
            type="button"
            onClick={() => setGalleryModalOpen(true)}
            className="w-[90px] h-[32px] px-2.5 text-[12px] font-medium rounded-[6px] transition-colors cursor-pointer whitespace-nowrap"
            style={{
              backgroundColor: '#1E1E26',
              border: '1px solid #2E2E3A',
              color: '#F4F4F5',
            }}
          >
            Gallery {capturedGallery.length > 0 ? `(${capturedGallery.length})` : ''}
          </button>

          <button
            type="button"
            onClick={() => setRepoModalOpen(true)}
            title="Inspect Native Windows Python PyQt6 Source Code Repository"
            className="h-[32px] px-2.5 text-[11px] font-semibold rounded-[6px] transition-colors cursor-pointer whitespace-nowrap"
            style={{
              backgroundColor: '#14141A',
              border: '1px solid #2E2E3A',
              color: '#E5A93C',
            }}
          >
            Python Source
          </button>
        </div>
      </header>

      {/* MAIN 2-COLUMN WORKSPACE: Left/Center Hero Viewport (~76%) + Single Right Studio Sidebar (350px) */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* 2. LEFT/CENTER HERO VIEWPORT + CLEAN BOTTOM CAPTURE BAR */}
        <main
          className="flex-1 flex flex-col min-w-0 overflow-hidden"
          style={{ backgroundColor: '#09090B' }}
        >
          {/* Unobstructed 16:9 Video Canvas Area with 24px breathing margin */}
          <div className="flex-1 min-h-0 relative">
            <ViewportCanvas
              params={params}
              isRecording={isRecording}
              recordingTimeSec={recordingSec}
              countdownValue={countdownVal}
              flashTrigger={flashActive}
              useLiveWebcam={useLiveWebcam}
              onCaptureDataUrlReady={handleCaptureGetterReady}
              onTelemetryUpdate={setTelemetry}
            />
          </div>

          {/* Clean Bottom Capture Bar (68px height, centered below video, 5 controls with 16px spacing) */}
          <div
            className="h-[68px] shrink-0 px-6 flex items-center justify-center gap-[16px]"
            style={{
              backgroundColor: '#0D0D10',
              borderTop: '1px solid #22222A',
            }}
          >
            {/* 1. Timer Selector (105px x 34px) */}
            <select
              aria-label="Capture Timer Selector"
              value={params.timer_sec}
              onChange={(e) =>
                updateParam(
                  'timer_sec',
                  Number(e.target.value) as 0 | 3 | 5 | 10
                )
              }
              className="w-[105px] h-[34px] px-2.5 text-[12px] font-medium rounded-[6px] outline-none cursor-pointer"
              style={{
                backgroundColor: '#1E1E26',
                border: '1px solid #2E2E3A',
                color: '#F4F4F5',
              }}
            >
              <option value={0}>Timer: Off</option>
              <option value={3}>Timer: 3s</option>
              <option value={5}>Timer: 5s</option>
              <option value={10}>Timer: 10s</option>
            </select>

            {/* 2. Screen Flash Toggle (110px x 34px) */}
            <button
              type="button"
              onClick={() => updateParam('screen_flash', !params.screen_flash)}
              className="w-[110px] h-[34px] px-3 text-[12px] font-semibold rounded-[6px] transition-colors cursor-pointer whitespace-nowrap"
              style={{
                backgroundColor: params.screen_flash
                  ? 'rgba(229, 169, 60, 0.16)'
                  : '#1E1E26',
                border: params.screen_flash
                  ? '1px solid #E5A93C'
                  : '1px solid #2E2E3A',
                color: params.screen_flash ? '#E5A93C' : '#F4F4F5',
              }}
            >
              Flash: {params.screen_flash ? 'On' : 'Off'}
            </button>

            {/* 3. Primary Photo Shutter Button (50px x 50px crisp white circle) */}
            <button
              type="button"
              aria-label="Take Photo Snapshot"
              onClick={handleTriggerPhoto}
              className="w-[50px] h-[50px] rounded-full flex items-center justify-center transition-transform active:scale-95 cursor-pointer shrink-0"
              style={{
                border: '2px solid #E5A93C',
                backgroundColor: 'transparent',
              }}
            >
              <span
                className="w-[38px] h-[38px] rounded-full block transition-colors"
                style={{ backgroundColor: '#F4F4F5' }}
              />
            </button>

            {/* 4. Primary Video Record Button (50px x 50px crimson circle / square stop icon) */}
            <button
              type="button"
              aria-label={isRecording ? 'Stop Recording' : 'Start Video Recording'}
              onClick={() => {
                setIsRecording((prev) => {
                  const next = !prev;
                  showNotice(
                    next
                      ? 'Started MP4 + WAV recording'
                      : 'Saved MP4 recording to Captures'
                  );
                  return next;
                });
              }}
              className="w-[50px] h-[50px] rounded-full flex items-center justify-center transition-transform active:scale-95 cursor-pointer shrink-0"
              style={{
                border: isRecording
                  ? '2px solid #EF4444'
                  : '2px solid #52525E',
                backgroundColor: 'transparent',
              }}
            >
              {isRecording ? (
                <span
                  className="w-[20px] h-[20px] rounded-[4px] block"
                  style={{ backgroundColor: '#EF4444' }}
                />
              ) : (
                <span
                  className="w-[34px] h-[34px] rounded-full block"
                  style={{ backgroundColor: '#EF4444' }}
                />
              )}
            </button>

            {/* Live Recording Timer Pill (Visible ONLY while recording) */}
            {isRecording && (
              <div
                className="h-[28px] px-3 rounded-[14px] flex items-center justify-center"
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #EF4444',
                }}
              >
                <span
                  className="text-[11px] font-bold"
                  style={{
                    color: '#EF4444',
                    fontFamily: '"JetBrains Mono", Consolas, monospace',
                  }}
                >
                  {formatRecordTimer(recordingSec)}
                </span>
              </div>
            )}

            {/* 5. Virtual Cam Button (135px x 34px) */}
            <button
              type="button"
              onClick={() => {
                const next = !params.virtual_cam_active;
                updateParam('virtual_cam_active', next);
                showNotice(
                  next
                    ? 'Virtual Cam Live (1280x720 @ 30fps)'
                    : 'Virtual Cam Stopped'
                );
              }}
              className="w-[135px] h-[34px] px-3 text-[12px] font-semibold rounded-[6px] transition-colors cursor-pointer whitespace-nowrap"
              style={{
                backgroundColor: params.virtual_cam_active
                  ? 'rgba(16, 185, 129, 0.16)'
                  : '#1E1E26',
                border: params.virtual_cam_active
                  ? '1px solid #10B981'
                  : '1px solid #2E2E3A',
                color: params.virtual_cam_active ? '#10B981' : '#F4F4F5',
              }}
            >
              Virtual Cam: {params.virtual_cam_active ? 'On' : 'Off'}
            </button>
          </div>
        </main>

        {/* 3. SINGLE RIGHT STUDIO SIDEBAR (350px fixed width, #111115) */}
        <aside
          className="w-[350px] shrink-0 flex flex-col h-full overflow-hidden"
          style={{
            backgroundColor: '#111115',
            borderLeft: '1px solid #22222A',
          }}
        >
          {/* 4-Tab Segmented Switcher (38px height, full-width equal columns) */}
          <div className="p-3 pb-0 shrink-0">
            <div
              className="h-[38px] grid grid-cols-4 p-1 rounded-[7px] gap-1"
              style={{
                backgroundColor: '#14141A',
                border: '1px solid #23232C',
              }}
            >
              {(
                [
                  { id: 'light', label: '1. Light' },
                  { id: 'color', label: '2. Color' },
                  { id: 'frame', label: '3. Frame' },
                  { id: 'studio', label: '4. Studio' },
                ] as { id: SidebarTab; label: string }[]
              ).map((tab) => {
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className="h-full rounded-[5px] text-[12px] transition-colors cursor-pointer whitespace-nowrap"
                    style={{
                      backgroundColor: active ? '#24242F' : 'transparent',
                      border: active
                        ? '1px solid #E5A93C'
                        : '1px solid transparent',
                      color: active ? '#F4F4F5' : '#A1A1AA',
                      fontWeight: active ? 600 : 500,
                    }}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Scrollable Tab Content Area (16px padding, 14px vertical spacing) */}
          <div className="flex-1 overflow-y-auto p-[16px] flex flex-col gap-[14px]">
            {activeTab === 'light' && (
              <StudioCard title="EXPOSURE & ROOM LIGHTING">
                {/* 1. Auto Exposure Toggle (Default: ON) */}
                <ToggleRow
                  label="Auto Exposure (RightLight)"
                  checked={params.auto_exposure}
                  onChange={(checked) => {
                    updateParam('auto_exposure', checked);
                    updateParam('manual_exposure', !checked);
                  }}
                />

                {/* 2. Manual Shutter Exposure (-11 EV to -2 EV, enabled only when Auto Exposure is OFF) */}
                <div
                  className={
                    params.auto_exposure
                      ? 'opacity-40 pointer-events-none transition-opacity'
                      : 'transition-opacity'
                  }
                >
                  <PrecisionSliderRow
                    label="Manual Shutter Exposure"
                    value={params.exposure_ev}
                    min={-11}
                    max={-2}
                    defaultValue={-5}
                    unit=" EV"
                    onChange={(v) => updateParam('exposure_ev', v)}
                  />
                </div>

                {/* 3. Smart Light Boost (Dark Room Lift) */}
                <PrecisionSliderRow
                  label="Smart Light Boost (Dark Room Lift)"
                  value={params.smart_light_boost}
                  min={0}
                  max={100}
                  defaultValue={0}
                  unit="%"
                  onChange={(v) => updateParam('smart_light_boost', v)}
                />

                {/* 4. Brightness */}
                <PrecisionSliderRow
                  label="Brightness"
                  value={params.hw_brightness}
                  min={0}
                  max={255}
                  defaultValue={128}
                  onChange={(v) => updateParam('hw_brightness', v)}
                />

                {/* 5. Contrast */}
                <PrecisionSliderRow
                  label="Contrast"
                  value={params.hw_contrast}
                  min={0}
                  max={255}
                  defaultValue={128}
                  onChange={(v) => updateParam('hw_contrast', v)}
                />

                {/* 6. Highlight Roll-Off (S-Curve) */}
                <PrecisionSliderRow
                  label="Highlight Roll-Off (Tone Curve)"
                  value={params.s_curve}
                  min={0}
                  max={100}
                  defaultValue={0}
                  unit="%"
                  onChange={(v) => updateParam('s_curve', v)}
                />

                {/* 7. Optical Sharpness */}
                <PrecisionSliderRow
                  label="Optical Sharpness"
                  value={params.hw_sharpness}
                  min={0}
                  max={255}
                  defaultValue={128}
                  onChange={(v) => updateParam('hw_sharpness', v)}
                />
              </StudioCard>
            )}

            {activeTab === 'color' && (
              <>
                {/* Card 1: Studio Look (2-column x 3-row grid of 6 looks) */}
                <StudioCard title="STUDIO LOOK">
                  <div className="grid grid-cols-2 gap-2">
                    {STUDIO_LOOK_NAMES.map((lookName: StudioLookName) => {
                      const selected = params.active_lut === lookName;
                      return (
                        <button
                          key={lookName}
                          type="button"
                          onClick={() => updateParam('active_lut', lookName)}
                          className="h-[34px] px-2.5 rounded-[6px] text-[12px] transition-colors cursor-pointer truncate"
                          style={{
                            backgroundColor: selected
                              ? 'rgba(229, 169, 60, 0.16)'
                              : '#1E1E26',
                            border: selected
                              ? '1px solid #E5A93C'
                              : '1px solid #2E2E3A',
                            color: selected ? '#E5A93C' : '#F4F4F5',
                            fontWeight: selected ? 600 : 500,
                          }}
                        >
                          {lookName}
                        </button>
                      );
                    })}
                  </div>

                  <PrecisionSliderRow
                    label="Look Intensity"
                    value={params.lut_intensity}
                    min={0}
                    max={100}
                    defaultValue={75}
                    unit="%"
                    onChange={(v) => updateParam('lut_intensity', v)}
                  />
                </StudioCard>

                {/* Card 2: White Balance & Color */}
                <StudioCard title="WHITE BALANCE & COLOR">
                  <ToggleRow
                    label="Auto White Balance"
                    checked={params.auto_wb}
                    onChange={(v) => updateParam('auto_wb', v)}
                  />

                  <PrecisionSliderRow
                    label="Temperature (Warmth)"
                    value={params.temp_shift}
                    min={-50}
                    max={50}
                    defaultValue={0}
                    onChange={(v) => updateParam('temp_shift', v)}
                  />

                  <PrecisionSliderRow
                    label="Tint (Green / Magenta)"
                    value={params.tint}
                    min={-50}
                    max={50}
                    defaultValue={0}
                    onChange={(v) => updateParam('tint', v)}
                  />

                  <PrecisionSliderRow
                    label="Saturation"
                    value={params.hw_saturation}
                    min={0}
                    max={255}
                    defaultValue={128}
                    onChange={(v) => updateParam('hw_saturation', v)}
                  />

                  <PrecisionSliderRow
                    label="Natural Vibrance"
                    value={params.vibrance}
                    min={-50}
                    max={50}
                    defaultValue={0}
                    onChange={(v) => updateParam('vibrance', v)}
                  />
                </StudioCard>
              </>
            )}

            {activeTab === 'frame' && (
              <>
                {/* Card 1: Digital PTZ & Geometry */}
                <StudioCard title="DIGITAL PTZ & GEOMETRY">
                  <PrecisionSliderRow
                    label="Optical Zoom"
                    value={params.zoom}
                    min={100}
                    max={300}
                    defaultValue={100}
                    unit="%"
                    onChange={(v) => updateParam('zoom', v)}
                  />

                  <PrecisionSliderRow
                    label="Horizontal Pan"
                    value={params.pan_x}
                    min={-100}
                    max={100}
                    defaultValue={0}
                    unit="%"
                    onChange={(v) => updateParam('pan_x', v)}
                  />

                  <PrecisionSliderRow
                    label="Vertical Tilt"
                    value={params.tilt_y}
                    min={-100}
                    max={100}
                    defaultValue={0}
                    unit="%"
                    onChange={(v) => updateParam('tilt_y', v)}
                  />

                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => updateParam('mirror_h', !params.mirror_h)}
                      className="h-[34px] rounded-[6px] text-[12px] font-medium cursor-pointer transition-colors"
                      style={{
                        backgroundColor: params.mirror_h
                          ? 'rgba(229, 169, 60, 0.16)'
                          : '#1E1E26',
                        border: params.mirror_h
                          ? '1px solid #E5A93C'
                          : '1px solid #2E2E3A',
                        color: params.mirror_h ? '#E5A93C' : '#F4F4F5',
                      }}
                    >
                      Mirror H
                    </button>

                    <button
                      type="button"
                      onClick={() => updateParam('flip_v', !params.flip_v)}
                      className="h-[34px] rounded-[6px] text-[12px] font-medium cursor-pointer transition-colors"
                      style={{
                        backgroundColor: params.flip_v
                          ? 'rgba(229, 169, 60, 0.16)'
                          : '#1E1E26',
                        border: params.flip_v
                          ? '1px solid #E5A93C'
                          : '1px solid #2E2E3A',
                        color: params.flip_v ? '#E5A93C' : '#F4F4F5',
                      }}
                    >
                      Flip V
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        updateParam(
                          'rotation_deg',
                          ((params.rotation_deg + 90) % 360) as
                            | 0
                            | 90
                            | 180
                            | 270
                        )
                      }
                      className="h-[34px] rounded-[6px] text-[12px] font-medium cursor-pointer transition-colors"
                      style={{
                        backgroundColor:
                          params.rotation_deg !== 0
                            ? 'rgba(229, 169, 60, 0.16)'
                            : '#1E1E26',
                        border:
                          params.rotation_deg !== 0
                            ? '1px solid #E5A93C'
                            : '1px solid #2E2E3A',
                        color:
                          params.rotation_deg !== 0 ? '#E5A93C' : '#F4F4F5',
                      }}
                    >
                      Rotate 90°
                    </button>
                  </div>
                </StudioCard>

                {/* Card 2: Subject Focus & Background (Default: OFF) */}
                <StudioCard title="SUBJECT FOCUS & BACKGROUND">
                  <ToggleRow
                    label="AI Smart Face Centering"
                    checked={params.ai_auto_frame}
                    onChange={(v) => updateParam('ai_auto_frame', v)}
                  />

                  <div className="flex flex-col gap-1.5">
                    <span className="text-[12px] font-medium text-[#F4F4F5]">
                      Background Mode
                    </span>
                    <select
                      aria-label="Background Mode"
                      value={params.bg_mode}
                      onChange={(e) =>
                        updateParam('bg_mode', e.target.value as BackgroundMode)
                      }
                      className="w-full h-[34px] px-2.5 text-[12px] font-medium rounded-[6px] outline-none cursor-pointer"
                      style={{
                        backgroundColor: '#1E1E26',
                        border: '1px solid #2E2E3A',
                        color: '#F4F4F5',
                      }}
                    >
                      <option value="Off (Natural Background)">
                        Off (Natural Background)
                      </option>
                      <option value="Subtle Studio Spotlight">
                        Subtle Studio Spotlight
                      </option>
                      <option value="Soft Bokeh Blur">Soft Bokeh Blur</option>
                      <option value="Custom Backdrop">Custom Backdrop</option>
                    </select>
                  </div>

                  <div
                    className={
                      params.bg_mode === 'Off (Natural Background)'
                        ? 'opacity-40 pointer-events-none transition-opacity'
                        : 'transition-opacity'
                    }
                  >
                    <PrecisionSliderRow
                      label="Effect Strength"
                      value={
                        params.bg_mode === 'Soft Bokeh Blur'
                          ? params.bokeh_strength
                          : params.spotlight_dim
                      }
                      min={0}
                      max={85}
                      defaultValue={35}
                      unit="%"
                      onChange={(v) => {
                        if (params.bg_mode === 'Soft Bokeh Blur') {
                          updateParam('bokeh_strength', Math.max(5, v));
                        } else {
                          updateParam('spotlight_dim', v);
                        }
                      }}
                    />
                  </div>
                </StudioCard>
              </>
            )}

            {activeTab === 'studio' && (
              <>
                {/* Card 1: Quick Studio Presets */}
                <StudioCard title="QUICK STUDIO PRESETS">
                  <div className="grid grid-cols-2 gap-2">
                    {Object.keys(FACTORY_PRESETS).map((presetName) => {
                      const active = params.active_preset_name === presetName;
                      return (
                        <button
                          key={presetName}
                          type="button"
                          onClick={() => handleApplyPreset(presetName)}
                          className="h-[34px] px-2.5 rounded-[6px] text-[12px] transition-colors cursor-pointer truncate"
                          style={{
                            backgroundColor: active
                              ? 'rgba(229, 169, 60, 0.16)'
                              : '#1E1E26',
                            border: active
                              ? '1px solid #E5A93C'
                              : '1px solid #2E2E3A',
                            color: active ? '#E5A93C' : '#F4F4F5',
                            fontWeight: active ? 600 : 500,
                          }}
                        >
                          {presetName}
                        </button>
                      );
                    })}
                  </div>
                </StudioCard>

                {/* Card 2: Viewport Guides & Output */}
                <StudioCard title="VIEWPORT GUIDES & OUTPUT">
                  <ToggleRow
                    label="Rule-of-Thirds Grid"
                    checked={params.show_grid}
                    onChange={(v) => updateParam('show_grid', v)}
                  />

                  <ToggleRow
                    label="2.35:1 Cinema Letterbox Bars"
                    checked={params.show_cinema_bars}
                    onChange={(v) => updateParam('show_cinema_bars', v)}
                  />

                  <ToggleRow
                    label="Show Corner Histogram & Mic Meter"
                    checked={params.show_corner_hud}
                    onChange={(v) => updateParam('show_corner_hud', v)}
                  />

                  <ToggleRow
                    label="1080p HD Super-Resolution Output"
                    checked={params.upscale_1080p}
                    onChange={(v) => updateParam('upscale_1080p', v)}
                  />
                </StudioCard>
              </>
            )}
          </div>
        </aside>
      </div>

      {/* GALLERY MODAL */}
      {galleryModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          style={{ backgroundColor: 'rgba(9, 9, 11, 0.82)' }}
        >
          <div
            className="w-full max-w-3xl rounded-[10px] p-5 flex flex-col gap-4 max-h-[82vh]"
            style={{
              backgroundColor: '#111115',
              border: '1px solid #23232C',
            }}
          >
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-[14px] font-bold text-[#F4F4F5]">
                  Captured Studio Stills ({capturedGallery.length})
                </h2>
                <p className="text-[11px] text-[#A1A1AA]">
                  Saved in lossless PNG format (~/Pictures/Leica_C270_Captures on Windows)
                </p>
              </div>
              <button
                type="button"
                onClick={() => setGalleryModalOpen(false)}
                className="h-[32px] px-3 text-[12px] font-medium rounded-[6px] cursor-pointer"
                style={{
                  backgroundColor: '#1E1E26',
                  border: '1px solid #2E2E3A',
                  color: '#F4F4F5',
                }}
              >
                Close
              </button>
            </div>

            {capturedGallery.length === 0 ? (
              <div
                className="py-16 text-center rounded-[8px] text-[12px] text-[#A1A1AA]"
                style={{
                  backgroundColor: '#18181E',
                  border: '1px solid #23232C',
                }}
              >
                No photos captured yet. Click the circular white shutter button in the bottom capture bar.
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 overflow-y-auto pr-1">
                {capturedGallery.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-[8px] p-2 flex flex-col gap-2"
                    style={{
                      backgroundColor: '#18181E',
                      border: '1px solid #23232C',
                    }}
                  >
                    <img
                      src={item.dataUrl}
                      alt={item.id}
                      className="w-full aspect-video object-cover rounded-[4px]"
                    />
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-[#F4F4F5] font-medium">
                        {item.look}
                      </span>
                      <a
                        href={item.dataUrl}
                        download={`${item.id}.png`}
                        className="text-[#E5A93C] font-semibold hover:underline"
                      >
                        Download
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* PYTHON SOURCE REPOSITORY MODAL */}
      <PythonRepoModal
        open={repoModalOpen}
        onClose={() => setRepoModalOpen(false)}
        repoFiles={repoFiles}
      />
    </div>
  );
}

/**
 * Clean Elevated Studio Card (#18181E with 1px solid #23232C border and 8px radius)
 */
function StudioCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-[8px] p-[14px] flex flex-col gap-[12px]"
      style={{
        backgroundColor: '#18181E',
        border: '1px solid #23232C',
      }}
    >
      <h3
        className="text-[11px] font-bold uppercase tracking-[1.0px]"
        style={{ color: '#A1A1AA' }}
      >
        {title}
      </h3>
      {children}
    </section>
  );
}

/**
 * Spacious 2-Row Precision Slider Row (46px height, double-click to reset to default)
 */
function PrecisionSliderRow({
  label,
  value,
  min,
  max,
  defaultValue,
  unit = '',
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  defaultValue: number;
  unit?: string;
  onChange: (val: number) => void;
}) {
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));

  return (
    <div
      className="h-[46px] flex flex-col justify-between select-none"
      onDoubleClick={() => onChange(defaultValue)}
      title="Double-click to reset to default"
    >
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-medium text-[#F4F4F5]">{label}</span>
        <span
          className="text-[12px] font-semibold"
          style={{
            color: '#E5A93C',
            fontFamily: '"JetBrains Mono", Consolas, monospace',
          }}
        >
          {value}
          {unit}
        </span>
      </div>
      <div className="relative h-[18px] flex items-center">
        <div
          className="w-full h-[5px] rounded-[3px] overflow-hidden"
          style={{ backgroundColor: '#272732' }}
        >
          <div
            className="h-full rounded-[3px]"
            style={{
              width: `${pct}%`,
              backgroundColor: '#E5A93C',
            }}
          />
        </div>
        <input
          type="range"
          aria-label={label}
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        <div
          className="pointer-events-none absolute w-[14px] h-[14px] rounded-full -translate-x-1/2"
          style={{
            left: `${pct}%`,
            backgroundColor: '#F4F4F5',
            border: '2px solid #E5A93C',
          }}
        />
      </div>
    </div>
  );
}

/**
 * Clean Toggle Switch Row (32px height)
 */
function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div
      onClick={() => onChange(!checked)}
      className="h-[32px] flex items-center justify-between cursor-pointer select-none"
    >
      <span className="text-[12px] font-medium text-[#F4F4F5]">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={(e) => {
          e.stopPropagation();
          onChange(!checked);
        }}
        className="w-[38px] h-[20px] rounded-full relative transition-colors cursor-pointer shrink-0"
        style={{
          backgroundColor: checked ? '#E5A93C' : '#272732',
          border: checked ? '1px solid #E5A93C' : '1px solid #383846',
        }}
      >
        <span
          className="w-[14px] h-[14px] rounded-full block transition-transform"
          style={{
            backgroundColor: checked ? '#09090B' : '#A1A1AA',
            transform: checked ? 'translateX(19px)' : 'translateX(2px)',
          }}
        />
      </button>
    </div>
  );
}
