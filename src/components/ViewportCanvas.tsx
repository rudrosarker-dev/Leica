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
  onTelemetryUpdate: (telemetry: {
    fps: number;
    processMs: number;
    resolution: string;
    webcamConnected: boolean;
  }) => void;
}

export const ViewportCanvas: React.FC<ViewportCanvasProps> = ({
  params,
  countdownValue,
  flashTrigger,
  useLiveWebcam,
  onCaptureDataUrlReady,
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

  // Expose frame capture callback for Photo Shutter
  useEffect(() => {
    onCaptureDataUrlReady(() => {
      if (!displayCanvasRef.current) return null;
      return displayCanvasRef.current.toDataURL('image/png', 1.0);
    });
  }, [onCaptureDataUrlReady]);

  // Manage live WebRTC webcam stream when requested
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

      // 1. Render Raw Sensor Frame (WebRTC Webcam OR Bright Daylight-Balanced Optical Studio Scene)
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

      // 2. Digital PTZ Crop (Skipped when zoom === 100 and no AI Auto-Frame)
      let targetZoom = bypassAll ? 100 : params.zoom;
      let targetPanX = bypassAll ? 0 : params.pan_x;
      let targetTiltY = bypassAll ? 0 : params.tilt_y;

      if (!bypassAll && params.ai_auto_frame) {
        targetZoom = Math.max(targetZoom, 128);
        targetPanX = Math.sin(now * 0.0008) * 14;
        targetTiltY = Math.cos(now * 0.0006) * 6 - 4;
      }

      const crop = computePTZCropRect(sw, sh, targetZoom, targetPanX, targetTiltY);

      // Draw PTZ cropped region onto display canvas (1280x720)
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

      // 3. FAST PATH: Only run pixel LUT pass if user moved a Light/Color slider or LUT
      const colorNeutral = isColorAndLightNeutral(params);
      const hasVignetteOrGrain =
        !bypassAll && (params.vignette > 0 || params.grain > 0);
      const hasManualExposureShift =
        !bypassAll && params.manual_exposure && !params.auto_exposure && params.exposure_ev !== -5;

      if (!colorNeutral || hasVignetteOrGrain || hasManualExposureShift || params.show_corner_hud) {
        const procW = 640;
        const procH = 360;
        sctx.drawImage(dispCanvas, 0, 0, procW, procH);
        const imgData = sctx.getImageData(0, 0, procW, procH);
        const data = imgData.data;

        if (!colorNeutral || hasManualExposureShift || hasVignetteOrGrain) {
          const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(params);
          const satFactor =
            1.0 + ((params.hw_saturation - 128) / 128.0) * 0.65;
          const vibNorm = (params.vibrance / 100.0) * 0.65;
          const applySat =
            Math.abs(satFactor - 1.0) > 0.01 || Math.abs(vibNorm) > 0.01;

          // Optional Manual Exposure EV factor (only when user disables Auto Exposure)
          const evDelta =
            hasManualExposureShift ? (params.exposure_ev - -5) * 0.14 : 0;
          const evMul = evDelta !== 0 ? Math.pow(2, evDelta) : 1.0;

          const vigStrength = !bypassAll ? (params.vignette / 100.0) * 0.65 : 0;
          const grainStrength = !bypassAll ? (params.grain / 100.0) * 20.0 : 0;

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

              // Apply 1D LUTs (includes Smart Light Boost, S-Curve, luminance-weighted Warmth/Tint & Look)
              r = rLUT[r | 0];
              g = gLUT[g | 0];
              b = bLUT[b | 0];

              if (applySat) {
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

              if (grainStrength > 0.2) {
                const noise =
                  (((x * 1973 + y * 9277 + frameCount * 26699) & 255) / 255.0 -
                    0.5) *
                  grainStrength;
                r += noise;
                g += noise;
                b += noise;
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

      // 4. Optional Background Mode (Skipped completely when "Off (Natural Background)" or Pure View Bypass)
      if (!bypassAll && params.bg_mode !== 'Off (Natural Background)') {
        applySubjectBackgroundEffect(dctx, dw, dh, now * 0.001, params);
      }

      // 5. Optional Studio Viewport Overlays (Rule-of-Thirds Grid, 2.35:1 Cinema Bars, Optional Corner Histogram)
      drawCleanViewportGuides(
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
        onTelemetryUpdate({
          fps: 30.0,
          processMs: Number(Math.max(0.8, procElapsed).toFixed(1)),
          resolution: params.upscale_1080p ? '1080p HD' : '720p HD',
          webcamConnected: webcamActiveRef.current,
        });
        lastTelemReport = now;
      }

      animId = requestAnimationFrame(renderLoop);
    };

    animId = requestAnimationFrame(renderLoop);
    return () => cancelAnimationFrame(animId);
  }, [params, countdownValue, flashTrigger, onTelemetryUpdate]);

  return (
    <div
      className="relative w-full h-full flex items-center justify-center p-[24px] select-none overflow-hidden"
      style={{ backgroundColor: '#09090B' }}
    >
      <video ref={videoRef} className="hidden" playsInline muted />
      <div
        className="relative w-full h-full flex items-center justify-center"
        style={{ maxWidth: '100%', maxHeight: '100%' }}
      >
        <canvas
          ref={displayCanvasRef}
          width={1280}
          height={720}
          className="max-w-full max-h-full aspect-video rounded-[6px] shadow-2xl"
          style={{
            border: '1px solid #22222A',
            backgroundColor: '#09090B',
          }}
        />
      </div>
    </div>
  );
};

/**
 * Renders a bright, well-lit, daylight-balanced natural studio scene
 * when no physical USB webcam is connected in the browser preview.
 */
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

  // Bright, airy modern studio room backdrop
  const bgGrad = ctx.createLinearGradient(0, 0, w, h);
  bgGrad.addColorStop(0, '#303642');
  bgGrad.addColorStop(0.5, '#262B35');
  bgGrad.addColorStop(1, '#1E222B');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, w, h);

  // Soft daylight window glow on upper left
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

  // Warm architectural studio lamp on right
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

  // Subtle studio acoustic shelf detail
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(w * 0.08, h * 0.14, w * 0.24, h * 0.34);

  // Color checker reference swatch card in upper right background
  const swatches = ['#D9534F', '#5CB85C', '#428BCA', '#F0AD4E', '#E8E8EC', '#2C2C34'];
  const cardX = w * 0.75;
  const cardY = h * 0.15;
  ctx.fillStyle = 'rgba(24, 24, 30, 0.72)';
  ctx.fillRect(cardX - 5, cardY - 5, 106, 40);
  swatches.forEach((col, i) => {
    ctx.fillStyle = col;
    ctx.fillRect(cardX + i * 16, cardY, 13, 30);
  });

  // Subject motion (natural breathing)
  const cx = w * 0.5 + Math.sin(t * 0.8) * 6;
  const cy = h * 0.44 + Math.cos(t * 0.65) * 3;

  // Shoulders / studio blazer
  ctx.fillStyle = '#252932';
  ctx.beginPath();
  ctx.ellipse(cx, h * 0.93, w * 0.24, h * 0.29, 0, 0, Math.PI * 2);
  ctx.fill();

  // Crewneck shirt collar
  ctx.fillStyle = '#E4E6EB';
  ctx.beginPath();
  ctx.ellipse(cx, h * 0.72, w * 0.065, h * 0.048, 0, 0, Math.PI * 2);
  ctx.fill();

  // Neck
  ctx.fillStyle = '#D9AC8E';
  ctx.fillRect(cx - 22, cy + 44, 44, 42);

  // Natural well-lit portrait face
  const faceGrad = ctx.createRadialGradient(
    cx - 12,
    cy - 14,
    8,
    cx,
    cy,
    76
  );
  faceGrad.addColorStop(0, '#F3C9AC');
  faceGrad.addColorStop(0.65, '#E4B596');
  faceGrad.addColorStop(1, '#C99778');
  ctx.fillStyle = faceGrad;
  ctx.beginPath();
  ctx.ellipse(cx, cy, 54, 68, 0, 0, Math.PI * 2);
  ctx.fill();

  // Hair silhouette
  ctx.fillStyle = '#231D1B';
  ctx.beginPath();
  ctx.ellipse(cx, cy - 46, 56, 30, 0, Math.PI, Math.PI * 2);
  ctx.fill();

  // Eyes & natural catchlights
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

  // Eyebrows
  ctx.strokeStyle = '#2D2420';
  ctx.lineWidth = 2.6;
  ctx.beginPath();
  ctx.moveTo(cx - 29, cy - 16);
  ctx.quadraticCurveTo(cx - 19, cy - 20, cx - 9, cy - 16);
  ctx.moveTo(cx + 9, cy - 16);
  ctx.quadraticCurveTo(cx + 19, cy - 20, cx + 29, cy - 16);
  ctx.stroke();

  // Smile contour
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

  if (params.bg_mode === 'Subtle Studio Spotlight') {
    const dimAlpha = (params.spotlight_dim / 100.0) * 0.75;
    const grad = ctx.createRadialGradient(cx, cy, h * 0.25, cx, cy, h * 0.72);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(1, `rgba(7, 7, 10, ${dimAlpha.toFixed(3)})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  } else if (params.bg_mode === 'Soft Bokeh Blur') {
    const blurAlpha = Math.min(0.65, params.bokeh_strength / 60.0);
    const grad = ctx.createRadialGradient(cx, cy, h * 0.26, cx, cy, h * 0.65);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(1, `rgba(22, 25, 34, ${blurAlpha.toFixed(3)})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  } else if (params.bg_mode === 'Custom Backdrop') {
    const grad = ctx.createRadialGradient(cx, cy, h * 0.26, cx, cy, h * 0.58);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(1, 'rgba(20, 22, 30, 0.92)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }
}

function drawCleanViewportGuides(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  params: StudioParams,
  hist: { r: number[]; g: number[]; b: number[]; luma: number[] },
  countdownValue: number,
  flashTrigger: boolean
) {
  ctx.save();

  // 1. Optional 2.35:1 Cinema Letterbox Bars
  if (params.show_cinema_bars) {
    const targetH = Math.round(w / 2.35);
    const barH = Math.max(0, Math.round((h - targetH) / 2));
    if (barH > 0) {
      ctx.fillStyle = 'rgba(7, 7, 9, 0.94)';
      ctx.fillRect(0, 0, w, barH);
      ctx.fillRect(0, h - barH, w, barH);
      ctx.strokeStyle = 'rgba(229, 169, 60, 0.35)';
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

  // 3. Optional Corner Histogram (Strictly OFF by default; only shown if user toggles it in Tab 4)
  if (params.show_corner_hud) {
    const hw = 168;
    const hh = 64;
    const hx = w - hw - 18;
    const hy = h - hh - 18;

    ctx.fillStyle = 'rgba(13, 13, 16, 0.82)';
    ctx.strokeStyle = '#272730';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(hx, hy, hw, hh, 6);
    ctx.fill();
    ctx.stroke();

    ctx.strokeStyle = '#E5A93C';
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    for (let i = 0; i < 64; i++) {
      const px = hx + 8 + (i / 63) * (hw - 16);
      const py = hy + hh - 8 - (hist.luma[i] / 100) * (hh - 20);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }

  // 4. Photo Countdown Number Overlay
  if (countdownValue > 0) {
    ctx.fillStyle = 'rgba(9, 9, 11, 0.45)';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#F4F4F5';
    ctx.font = '700 96px Inter, Segoe UI, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(countdownValue), w / 2, h / 2);
  }

  // 5. Screen Flash Overlay
  if (flashTrigger) {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.88)';
    ctx.fillRect(0, 0, w, h);
  }

  ctx.restore();
}
