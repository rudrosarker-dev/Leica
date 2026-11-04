import React, { useEffect, useRef } from 'react';
import {
  StudioParams,
  buildColorGradingLUTs,
  computePTZCropRect,
  computeRGBHistogram64,
  isColorAndLightNeutral,
} from '../utils/ispMath';

interface ViewportCanvasProps {
  params: StudioParams;
  isRecording: boolean;
  recordingTimeSec: number;
  countdownValue: number;
  flashTrigger: boolean;
  useLiveWebcam: boolean;
  onCaptureDataUrlReady: (getter: () => string | null) => void;
  onPTZChange?: (zoom: number, panX: number, tiltY: number) => void;
  onTelemetryUpdate: (telemetry: {
    fps: number;
    processMs: number;
    resolution: string;
    webcamConnected: boolean;
    audioDb: number;
  }) => void;
}

export const ViewportCanvas: React.FC<ViewportCanvasProps> = ({
  params,
  isRecording,
  countdownValue,
  flashTrigger,
  useLiveWebcam,
  onCaptureDataUrlReady,
  onPTZChange,
  onTelemetryUpdate,
}) => {
  const displayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const sourceCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const webcamActiveRef = useRef<boolean>(false);

  const histRef = useRef<{ r: number[]; g: number[]; b: number[]; luma: number[] }>({
    r: new Array(64).fill(0),
    g: new Array(64).fill(0),
    b: new Array(64).fill(0),
    luma: new Array(64).fill(0),
  });

  useEffect(() => {
    onCaptureDataUrlReady(() => {
      if (!displayCanvasRef.current) return null;
      return displayCanvasRef.current.toDataURL('image/png', 1.0);
    });
  }, [onCaptureDataUrlReady]);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;

    async function setupWebcam() {
      if (!useLiveWebcam) {
        webcamActiveRef.current = false;
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            frameRate: { ideal: 30 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          webcamActiveRef.current = true;
        }
      } catch {
        webcamActiveRef.current = false;
      }
    }

    setupWebcam();
    return () => {
      cancelled = true;
      webcamActiveRef.current = false;
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [useLiveWebcam]);

  useEffect(() => {
    let animId = 0;
    let frameCount = 0;
    let lastTelemReport = performance.now();

    if (!sourceCanvasRef.current) {
      sourceCanvasRef.current = document.createElement('canvas');
      sourceCanvasRef.current.width = 640;
      sourceCanvasRef.current.height = 360;
    }

    const renderLoop = (now: number) => {
      const startProc = performance.now();
      frameCount++;

      const dispCanvas = displayCanvasRef.current;
      const srcCanvas = sourceCanvasRef.current;
      if (!dispCanvas || !srcCanvas) {
        animId = requestAnimationFrame(renderLoop);
        return;
      }

      const sctx = srcCanvas.getContext('2d', { willReadFrequently: true });
      const dctx = dispCanvas.getContext('2d');
      if (!sctx || !dctx) {
        animId = requestAnimationFrame(renderLoop);
        return;
      }

      const sw = srcCanvas.width;
      const sh = srcCanvas.height;

      // 1. Render Raw Sensor Frame
      if (
        webcamActiveRef.current &&
        videoRef.current &&
        videoRef.current.readyState >= 2
      ) {
        sctx.save();
        if (params.mirror_h) {
          sctx.translate(sw, 0);
          sctx.scale(-1, 1);
        }
        if (params.flip_v) {
          sctx.translate(0, sh);
          sctx.scale(1, -1);
        }
        sctx.drawImage(videoRef.current, 0, 0, sw, sh);
        sctx.restore();
      } else {
        drawNaturalDaylightSubject(sctx, sw, sh, now * 0.001, params);
      }

      const bypassAll = params.pure_view_bypass;

      // 2. Digital PTZ Crop
      let targetZoom = bypassAll ? 100 : params.zoom;
      let targetPanX = bypassAll ? 0 : params.pan_x;
      let targetTiltY = bypassAll ? 0 : params.tilt_y;

      if (!bypassAll && params.ai_auto_frame) {
        targetZoom = Math.max(targetZoom, 135);
        targetPanX = Math.sin(now * 0.0008) * 14;
        targetTiltY = Math.cos(now * 0.0006) * 6 - 4;
      }

      const crop = computePTZCropRect(sw, sh, targetZoom, targetPanX, targetTiltY);

      const dw = dispCanvas.width;
      const dh = dispCanvas.height;

      dctx.save();
      dctx.clearRect(0, 0, dw, dh);

      if (!bypassAll && params.rotation_deg !== 0) {
        dctx.translate(dw / 2, dh / 2);
        dctx.rotate((params.rotation_deg * Math.PI) / 180);
        dctx.drawImage(
          srcCanvas,
          crop.x,
          crop.y,
          crop.width,
          crop.height,
          -dw / 2,
          -dh / 2,
          dw,
          dh
        );
      } else {
        dctx.drawImage(
          srcCanvas,
          crop.x,
          crop.y,
          crop.width,
          crop.height,
          0,
          0,
          dw,
          dh
        );
      }
      dctx.restore();

      // 3. Pixel LUT & Optical Grading Pass
      const colorNeutral = isColorAndLightNeutral(params);
      const hasVignette = !bypassAll && params.vignette > 0;
      const hasExposureShift = !bypassAll && params.exposure_ev !== -4;

      if (!colorNeutral || hasVignette || hasExposureShift || params.show_corner_hud) {
        const procW = 640;
        const procH = 360;
        sctx.drawImage(dispCanvas, 0, 0, procW, procH);
        const imgData = sctx.getImageData(0, 0, procW, procH);
        const data = imgData.data;

        if (!colorNeutral || hasExposureShift || hasVignette) {
          const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(params);
          const satFactor = 1.0 + ((params.hw_saturation - 32) / 128.0) * 0.65;
          const vibNorm = (params.vibrance / 100.0) * 0.65;
          const applySat =
            Math.abs(satFactor - 1.0) > 0.01 || Math.abs(vibNorm) > 0.01;

          const evDelta = hasExposureShift ? (params.exposure_ev - -4) * 0.12 : 0;
          const evMul = evDelta !== 0 ? Math.pow(2, evDelta) : 1.0;
          const vigStrength = !bypassAll ? (params.vignette / 100.0) * 0.65 : 0;

          let idx = 0;
          for (let y = 0; y < procH; y++) {
            const ny = (y - procH * 0.5) / (procH * 0.5);
            const ny2 = ny * ny;

            for (let x = 0; x < procW; x++) {
              let r = data[idx];
              let g = data[idx + 1];
              let b = data[idx + 2];

              if (evMul !== 1.0) {
                r = Math.min(255, Math.max(0, r * evMul));
                g = Math.min(255, Math.max(0, g * evMul));
                b = Math.min(255, Math.max(0, b * evMul));
              }

              r = rLUT[r | 0];
              g = gLUT[g | 0];
              b = bLUT[b | 0];

              if (applySat && params.active_lut !== 'Leica B&W') {
                const luma = 0.299 * r + 0.587 * g + 0.114 * b;
                const maxC = Math.max(r, g, b);
                const minC = Math.min(r, g, b);
                const curSat = (maxC - minC) / 255.0;
                const boost = satFactor + vibNorm * (1.0 - curSat);
                r = luma + (r - luma) * boost;
                g = luma + (g - luma) * boost;
                b = luma + (b - luma) * boost;
              }

              if (vigStrength > 0.005) {
                const nx = (x - procW * 0.5) / (procW * 0.5);
                const r2 = nx * nx + ny2;
                const vMask = Math.max(0.2, 1.0 - r2 * vigStrength);
                r *= vMask;
                g *= vMask;
                b *= vMask;
              }

              data[idx] = r <= 0 ? 0 : r >= 255 ? 255 : r;
              data[idx + 1] = g <= 0 ? 0 : g >= 255 ? 255 : g;
              data[idx + 2] = b <= 0 ? 0 : b >= 255 ? 255 : b;
              idx += 4;
            }
          }

          sctx.putImageData(imgData, 0, 0);
          dctx.drawImage(srcCanvas, 0, 0, procW, procH, 0, 0, dw, dh);
        }

        if (params.show_corner_hud && frameCount % 4 === 0) {
          histRef.current = computeRGBHistogram64(data, 16);
        }
      }

      // 4. Optional AI Portrait Studio Background Mode
      if (!bypassAll && params.bg_mode !== 'Off (Natural)') {
        applySubjectBackgroundEffect(dctx, dw, dh, now * 0.001, params);
      }

      // 5. EVF Reticle Corner Brackets [ ], Guides, Lower-Third & Flash
      drawEVFViewfinderOverlays(
        dctx,
        dw,
        dh,
        params,
        histRef.current,
        countdownValue,
        flashTrigger
      );

      const procElapsed = performance.now() - startProc;
      if (now - lastTelemReport >= 350) {
        // If 30-FPS Boost is unchecked, simulate the C270 10.0 FPS Low-Light Compensation drop
        const simulatedFps = params.unlock_30fps ? 30.0 : 10.0;
        const audioDb = -18 + Math.round(Math.sin(now * 0.004) * 6);
        onTelemetryUpdate({
          fps: simulatedFps,
          processMs: Number(Math.max(0.8, procElapsed).toFixed(1)),
          resolution: params.upscale_1080p ? '1080P LANCZOS' : '720P MJPG',
          webcamConnected: webcamActiveRef.current,
          audioDb,
        });
        lastTelemReport = now;
      }

      animId = requestAnimationFrame(renderLoop);
    };

    animId = requestAnimationFrame(renderLoop);
    return () => cancelAnimationFrame(animId);
  }, [params, countdownValue, flashTrigger, onTelemetryUpdate]);

  const handleWheelZoom = (e: React.WheelEvent<HTMLCanvasElement>) => {
    if (!onPTZChange) return;
    const step = e.deltaY < 0 ? 10 : -10;
    const nextZoom = Math.max(100, Math.min(300, params.zoom + step));
    onPTZChange(
      nextZoom,
      nextZoom === 100 ? 0 : params.pan_x,
      nextZoom === 100 ? 0 : params.tilt_y
    );
  };

  const simFps = params.unlock_30fps ? '30.0' : '10.0';
  const wbKelvin = Math.round(5500 + params.temp_shift * 18);

  return (
    <div
      className="relative w-full h-full flex flex-col items-center justify-between px-5 pt-4 pb-2.5 select-none overflow-hidden"
      style={{ backgroundColor: '#07070A' }}
    >
      <video ref={videoRef} className="hidden" playsInline muted />

      {/* Sunken Matte EVF Bezel Container */}
      <div className="relative flex-1 w-full min-h-0 flex items-center justify-center">
        <div
          className="relative flex items-center justify-center p-1 rounded-[6px]"
          style={{
            backgroundColor: '#040406',
            border: isRecording
              ? '1.5px solid #E11D48'
              : params.virtual_cam_active
              ? '1.5px solid #10B981'
              : '1px solid #22222E',
            boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.9)',
            maxWidth: '100%',
            maxHeight: '100%',
            aspectRatio: params.aspect_mode === '9:16' ? '9 / 16' : '16 / 9',
          }}
        >
          <canvas
            ref={displayCanvasRef}
            data-testid="evf-viewfinder-canvas"
            width={1280}
            height={720}
            onWheel={handleWheelZoom}
            onDoubleClick={() => onPTZChange?.(100, 0, 0)}
            className="w-full h-full object-contain rounded-[3px]"
            style={{ backgroundColor: '#09090B' }}
          />
        </div>
      </div>

      {/* LAW 2: Sleek Bottom EVF Optical Status Strip (SHUTTER | ISO/GAIN | WB KELVIN | FPS | CODEC | AUDIO VU) */}
      <div
        className="w-full max-w-[980px] h-[24px] mt-2 px-4 rounded-[3px] flex items-center justify-between text-[10px] font-mono font-bold tracking-[0.4px] tabular-nums shrink-0"
        style={{
          backgroundColor: '#0B0B10',
          border: '1px solid #22222E',
          color: '#D4D4DF',
        }}
      >
        <span>SHUTTER: {params.exposure_ev} EV (1/30s)</span>
        <span className="text-[#525264]">|</span>
        <span>ISO/GAIN: {params.hw_gain}</span>
        <span className="text-[#525264]">|</span>
        <span>WB: {wbKelvin}K</span>
        <span className="text-[#525264]">|</span>
        <span style={{ color: params.unlock_30fps ? '#10B981' : '#E5A93C' }}>
          FPS: {simFps}
        </span>
        <span className="text-[#525264]">|</span>
        <span>CODEC: MJPG 4:2:2</span>
        <span className="text-[#525264]">|</span>
        <span className="text-[#E5A93C]">SYNC: 1.0X WALL-CLOCK CFR</span>
      </div>
    </div>
  );
};

function drawNaturalDaylightSubject(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  t: number,
  params: StudioParams
) {
  ctx.save();
  if (params.mirror_h) {
    ctx.translate(w, 0);
    ctx.scale(-1, 1);
  }
  if (params.flip_v) {
    ctx.translate(0, h);
    ctx.scale(1, -1);
  }

  const bgGrad = ctx.createLinearGradient(0, 0, w, h);
  bgGrad.addColorStop(0, '#2B303C');
  bgGrad.addColorStop(0.5, '#222630');
  bgGrad.addColorStop(1, '#181B22');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, w, h);

  const keyLight = ctx.createRadialGradient(
    w * 0.25,
    h * 0.2,
    10,
    w * 0.25,
    h * 0.2,
    w * 0.55
  );
  keyLight.addColorStop(0, 'rgba(245, 240, 230, 0.22)');
  keyLight.addColorStop(1, 'rgba(245, 240, 230, 0)');
  ctx.fillStyle = keyLight;
  ctx.fillRect(0, 0, w, h);

  const warmLamp = ctx.createRadialGradient(
    w * 0.82,
    h * 0.28,
    8,
    w * 0.82,
    h * 0.28,
    w * 0.32
  );
  warmLamp.addColorStop(0, 'rgba(255, 215, 165, 0.28)');
  warmLamp.addColorStop(1, 'rgba(255, 215, 165, 0)');
  ctx.fillStyle = warmLamp;
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(w * 0.08, h * 0.14, w * 0.24, h * 0.34);

  const swatches = ['#D9534F', '#5CB85C', '#428BCA', '#F0AD4E', '#E8E8EC', '#2C2C34'];
  const cardX = w * 0.75;
  const cardY = h * 0.15;
  ctx.fillStyle = 'rgba(24, 24, 30, 0.72)';
  ctx.fillRect(cardX - 5, cardY - 5, 106, 40);
  swatches.forEach((col, i) => {
    ctx.fillStyle = col;
    ctx.fillRect(cardX + i * 16, cardY, 13, 30);
  });

  const cx = w * 0.5 + Math.sin(t * 0.8) * 6;
  const cy = h * 0.44 + Math.cos(t * 0.65) * 3;

  ctx.fillStyle = '#252932';
  ctx.beginPath();
  ctx.ellipse(cx, h * 0.93, w * 0.24, h * 0.29, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#E4E6EB';
  ctx.beginPath();
  ctx.ellipse(cx, h * 0.72, w * 0.065, h * 0.048, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#D9AC8E';
  ctx.fillRect(cx - 22, cy + 44, 44, 42);

  const faceGrad = ctx.createRadialGradient(cx - 12, cy - 14, 8, cx, cy, 76);
  faceGrad.addColorStop(0, '#F3C9AC');
  faceGrad.addColorStop(0.65, '#E4B596');
  faceGrad.addColorStop(1, '#C99778');
  ctx.fillStyle = faceGrad;
  ctx.beginPath();
  ctx.ellipse(cx, cy, 54, 68, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#231D1B';
  ctx.beginPath();
  ctx.ellipse(cx, cy - 46, 56, 30, 0, Math.PI, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#232020';
  ctx.beginPath();
  ctx.ellipse(cx - 19, cy - 6, 6.5, 4.2, 0, 0, Math.PI * 2);
  ctx.ellipse(cx + 19, cy - 6, 6.5, 4.2, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#FFFFFF';
  ctx.beginPath();
  ctx.arc(cx - 21, cy - 7.5, 1.8, 0, Math.PI * 2);
  ctx.arc(cx + 17, cy - 7.5, 1.8, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = '#2D2420';
  ctx.lineWidth = 2.6;
  ctx.beginPath();
  ctx.moveTo(cx - 29, cy - 16);
  ctx.quadraticCurveTo(cx - 19, cy - 20, cx - 9, cy - 16);
  ctx.moveTo(cx + 9, cy - 16);
  ctx.quadraticCurveTo(cx + 19, cy - 20, cx + 29, cy - 16);
  ctx.stroke();

  ctx.strokeStyle = '#AD6F5A';
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  ctx.arc(cx, cy + 20, 14, 0.15 * Math.PI, 0.85 * Math.PI);
  ctx.stroke();

  ctx.restore();
}

function applySubjectBackgroundEffect(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  t: number,
  params: StudioParams
) {
  const cx = w * 0.5 + Math.sin(t * 0.8) * 10;
  const cy = h * 0.54;

  if (params.bg_mode === 'Studio Dimmed Spotlight') {
    const dimAlpha = (params.bg_strength / 100.0) * 0.78;
    const grad = ctx.createRadialGradient(cx, cy, h * 0.25, cx, cy, h * 0.72);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(1, `rgba(6, 6, 9, ${dimAlpha.toFixed(3)})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  } else if (params.bg_mode === 'Optical Bokeh Blur') {
    const blurAlpha = Math.min(0.68, (params.bg_strength / 100.0) * 0.72);
    const grad = ctx.createRadialGradient(cx, cy, h * 0.26, cx, cy, h * 0.65);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(1, `rgba(22, 25, 34, ${blurAlpha.toFixed(3)})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  } else if (params.bg_mode === 'Custom Backdrop') {
    const grad = ctx.createRadialGradient(cx, cy, h * 0.26, cx, cy, h * 0.58);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(1, 'rgba(18, 20, 28, 0.92)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }
}

function drawEVFViewfinderOverlays(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  params: StudioParams,
  hist: { r: number[]; g: number[]; b: number[]; luma: number[] },
  countdownValue: number,
  flashTrigger: boolean
) {
  ctx.save();

  // 1. Optional 2.35:1 Cinema Scope Bars
  if (params.show_cinema_bars) {
    const targetH = Math.round(w / 2.35);
    const barH = Math.max(0, Math.round((h - targetH) / 2));
    if (barH > 0) {
      ctx.fillStyle = 'rgba(5, 5, 8, 0.95)';
      ctx.fillRect(0, 0, w, barH);
      ctx.fillRect(0, h - barH, w, barH);
      ctx.strokeStyle = 'rgba(229, 169, 60, 0.45)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, barH);
      ctx.lineTo(w, barH);
      ctx.moveTo(0, h - barH);
      ctx.lineTo(w, h - barH);
      ctx.stroke();
    }
  }

  // 2. Optional Rule-of-Thirds Grid
  if (params.show_grid) {
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(w / 3, 0);
    ctx.lineTo(w / 3, h);
    ctx.moveTo((w * 2) / 3, 0);
    ctx.lineTo((w * 2) / 3, h);
    ctx.moveTo(0, h / 3);
    ctx.lineTo(w, h / 3);
    ctx.moveTo(0, (h * 2) / 3);
    ctx.lineTo(w, (h * 2) / 3);
    ctx.stroke();
  }

  // 3. LAW 2: Crisp 20px L-Shaped EVF Viewfinder Corner Reticle Brackets in #E5A93C
  const arm = 24;
  const inset = 16;
  ctx.strokeStyle = '#E5A93C';
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  // Top-Left
  ctx.moveTo(inset, inset + arm);
  ctx.lineTo(inset, inset);
  ctx.lineTo(inset + arm, inset);
  // Top-Right
  ctx.moveTo(w - inset - arm, inset);
  ctx.lineTo(w - inset, inset);
  ctx.lineTo(w - inset, inset + arm);
  // Bottom-Left
  ctx.moveTo(inset, h - inset - arm);
  ctx.lineTo(inset, h - inset);
  ctx.lineTo(inset + arm, h - inset);
  // Bottom-Right
  ctx.moveTo(w - inset - arm, h - inset);
  ctx.lineTo(w - inset, h - inset);
  ctx.lineTo(w - inset, h - inset - arm);
  ctx.stroke();

  // 4. Optional Lower-Third Name Tag
  if (!params.pure_view_bypass && params.show_lower_third) {
    const lx = 42;
    const ly = h - 106;
    const lw = 340;
    const lh = 62;
    ctx.fillStyle = 'rgba(12, 12, 16, 0.86)';
    ctx.strokeStyle = '#3E3E50';
    ctx.lineWidth = 1;
    ctx.fillRect(lx, ly, lw, lh);
    ctx.strokeRect(lx, ly, lw, lh);
    ctx.fillStyle = '#E5A93C';
    ctx.fillRect(lx, ly, 4, lh);

    ctx.fillStyle = '#F4F4F6';
    ctx.font = '700 18px "Plus Jakarta Sans", "Segoe UI", sans-serif';
    ctx.fillText(params.lower_third_name || 'Alex Morgan', lx + 16, ly + 26);

    ctx.fillStyle = '#A1A1B0';
    ctx.font = '600 13px "JetBrains Mono", Consolas, monospace';
    ctx.fillText(
      params.lower_third_title || 'Cinema Systems Architect',
      lx + 16,
      ly + 47
    );
  }

  // 5. Optional Corner RGB Histogram
  if (params.show_corner_hud) {
    const hw = 176;
    const hh = 72;
    const hx = w - hw - 26;
    const hy = 26;

    ctx.fillStyle = 'rgba(10, 10, 14, 0.86)';
    ctx.strokeStyle = '#3E3E50';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(hx, hy, hw, hh, 5);
    ctx.fill();
    ctx.stroke();

    const channels: { arr: number[]; color: string }[] = [
      { arr: hist.b, color: '#0EA5E9' },
      { arr: hist.g, color: '#10B981' },
      { arr: hist.r, color: '#F43F5E' },
      { arr: hist.luma, color: '#E5A93C' },
    ];
    for (const ch of channels) {
      ctx.strokeStyle = ch.color;
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      for (let i = 0; i < 64; i++) {
        const px = hx + 8 + (i / 63) * (hw - 16);
        const py = hy + hh - 8 - (ch.arr[i] / 100) * (hh - 18);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    }
  }

  // 6. Countdown Overlay
  if (countdownValue > 0) {
    ctx.fillStyle = 'rgba(9, 9, 11, 0.45)';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#F4F4F5';
    ctx.font = '700 96px "JetBrains Mono", Consolas, monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(countdownValue), w / 2, h / 2);
  }

  // 7. Softbox Flash Overlay
  if (flashTrigger) {
    ctx.fillStyle = 'rgba(255, 253, 248, 0.88)';
    ctx.fillRect(0, 0, w, h);
  }

  ctx.restore();
}
