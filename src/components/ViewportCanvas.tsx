import React, { useEffect, useRef, useState } from "react";
import {
  StudioParams,
  build256LUT,
  computeHistogram64FromRGBA,
  stepGimbalEMA,
  clamp,
} from "../utils/ispMath";

export interface ViewportCanvasProps {
  params: StudioParams;
  customCubeLut: { r: Float32Array; g: Float32Array; b: Float32Array } | null;
  backdropImageElement: HTMLImageElement | null;
  watermarkImageElement: HTMLImageElement | null;
  isRecording: boolean;
  isVirtualCam: boolean;
  countdownValue: number;
  flashTriggerCounter: number;
  captureRequestCounter: number;
  onFrameCaptured: (dataUrl: string, width: number, height: number) => void;
  onFpsUpdated: (fps: number) => void;
  onPtzDragged: (zoom: number, panX: number, tiltY: number) => void;
  onPtzReset: () => void;
}

export const ViewportCanvas: React.FC<ViewportCanvasProps> = ({
  params,
  customCubeLut,
  backdropImageElement,
  watermarkImageElement,
  isRecording,
  isVirtualCam,
  countdownValue,
  flashTriggerCounter,
  captureRequestCounter,
  onFrameCaptured,
  onFpsUpdated,
  onPtzDragged,
  onPtzReset,
}) => {
  const displayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const dragLastPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Store mutable refs so the requestAnimationFrame loop never tears down on slider state updates
  const paramsRef = useRef<StudioParams>(params);
  paramsRef.current = params;

  const customCubeRef = useRef(customCubeLut);
  customCubeRef.current = customCubeLut;

  const backdropImgRef = useRef(backdropImageElement);
  backdropImgRef.current = backdropImageElement;

  const watermarkImgRef = useRef(watermarkImageElement);
  watermarkImgRef.current = watermarkImageElement;

  const isRecRef = useRef(isRecording);
  isRecRef.current = isRecording;

  const isVcamRef = useRef(isVirtualCam);
  isVcamRef.current = isVirtualCam;

  const countdownRef = useRef(countdownValue);
  countdownRef.current = countdownValue;

  const onFrameCapturedRef = useRef(onFrameCaptured);
  onFrameCapturedRef.current = onFrameCaptured;

  const onFpsUpdatedRef = useRef(onFpsUpdated);
  onFpsUpdatedRef.current = onFpsUpdated;

  const gimbalRef = useRef({ zoom: 1.0, panX: 0.0, panY: 0.0 });
  const flashAlphaRef = useRef(0.0);
  const flashHoldFramesRef = useRef(0);
  const lastCaptureProcessedRef = useRef(captureRequestCounter);

  // Audio WebAudio API analyzer state
  const audioLevelRef = useRef<{ rmsDb: number; peakDb: number; liveMic: boolean }>({
    rmsDb: -42.0,
    peakDb: -28.0,
    liveMic: false,
  });

  useEffect(() => {
    if (flashTriggerCounter > 0) {
      flashAlphaRef.current = 1.0;
      flashHoldFramesRef.current = 15; // ~280ms hold before fade
    }
  }, [flashTriggerCounter]);

  // Attempt live WebRTC camera and microphone connection with automatic optical fallback
  useEffect(() => {
    let mediaStream: MediaStream | null = null;
    let audioCtx: AudioContext | null = null;
    let animAudioId = 0;

    const videoEl = document.createElement("video");
    videoEl.playsInline = true;
    videoEl.muted = true;
    videoRef.current = videoEl;

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices
        .getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
          audio: true,
        })
        .then((stream) => {
          mediaStream = stream;
          videoEl.srcObject = stream;
          videoEl.play().catch(() => {});

          if (stream.getAudioTracks().length > 0) {
            try {
              audioCtx = new AudioContext();
              const source = audioCtx.createMediaStreamSource(stream);
              const analyser = audioCtx.createAnalyser();
              analyser.fftSize = 512;
              source.connect(analyser);
              const data = new Float32Array(analyser.fftSize);

              const updateAudio = () => {
                analyser.getFloatTimeDomainData(data);
                let sumSq = 0;
                let peak = 0;
                for (let i = 0; i < data.length; i++) {
                  const s = Math.abs(data[i]);
                  sumSq += s * s;
                  if (s > peak) peak = s;
                }
                const rms = Math.sqrt(sumSq / data.length);
                const rmsDb = clamp(20 * Math.log10(Math.max(rms, 1e-7)), -60, 0);
                const peakDb = clamp(20 * Math.log10(Math.max(peak, 1e-7)), -60, 0);
                audioLevelRef.current.rmsDb = rmsDb;
                audioLevelRef.current.peakDb = Math.max(
                  rmsDb,
                  peakDb,
                  audioLevelRef.current.peakDb - 0.4
                );
                audioLevelRef.current.liveMic = true;
                animAudioId = requestAnimationFrame(updateAudio);
              };
              updateAudio();
            } catch {
              // Fallback to studio tone modulation
            }
          }
        })
        .catch(() => {
          // No physical camera/mic in headless environment; optical reference scene runs automatically
        });
    }

    return () => {
      if (animAudioId) cancelAnimationFrame(animAudioId);
      if (audioCtx) audioCtx.close().catch(() => {});
      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  // Main 30-FPS ISP & HUD Render Loop
  useEffect(() => {
    const procCanvas = document.createElement("canvas");
    procCanvas.width = 640;
    procCanvas.height = 360;
    const procCtx = procCanvas.getContext("2d", { willReadFrequently: true });

    let rafId = 0;
    let lastTime = performance.now();
    const frameIntervals: number[] = [];

    const drawSyntheticReferenceScene = (
      ctx: CanvasRenderingContext2D,
      w: number,
      h: number,
      tSec: number,
      p: StudioParams
    ) => {
      // Simulate hardware exposure & gain brightness response
      const expFactor = p.manual_exposure_lock
        ? Math.pow(1.12, p.hardware_exposure + 5) * (p.hardware_gain / 110.0)
        : 1.0;
      const hwBrightOffset = (p.hardware_brightness - 128) * 0.6;

      // Studio ambient gradient backdrop
      const bgGrad = ctx.createLinearGradient(0, 0, w, h);
      bgGrad.addColorStop(0, "#1E2028");
      bgGrad.addColorStop(0.55, "#14161D");
      bgGrad.addColorStop(1, "#0E1015");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Practical studio warm key light bokeh orb in upper right
      const keyGrad = ctx.createRadialGradient(w * 0.76, h * 0.24, 6, w * 0.76, h * 0.24, w * 0.28);
      keyGrad.addColorStop(0, "rgba(229, 169, 60, 0.42)");
      keyGrad.addColorStop(0.5, "rgba(229, 169, 60, 0.12)");
      keyGrad.addColorStop(1, "rgba(229, 169, 60, 0)");
      ctx.fillStyle = keyGrad;
      ctx.fillRect(0, 0, w, h);

      // Cool rim light on left background
      const rimGrad = ctx.createRadialGradient(w * 0.2, h * 0.32, 4, w * 0.2, h * 0.32, w * 0.25);
      rimGrad.addColorStop(0, "rgba(56, 189, 248, 0.22)");
      rimGrad.addColorStop(1, "rgba(56, 189, 248, 0)");
      ctx.fillStyle = rimGrad;
      ctx.fillRect(0, 0, w, h);

      // Subject subtle natural motion
      const cx = w * 0.5 + Math.sin(tSec * 0.85) * 9;
      const cy = h * 0.42 + Math.cos(tSec * 0.6) * 4;

      // Shoulders / Coat
      ctx.fillStyle = "#1B1C22";
      ctx.beginPath();
      ctx.ellipse(cx, h * 0.88, w * 0.21, h * 0.34, 0, 0, Math.PI * 2);
      ctx.fill();

      // Collar detail
      ctx.strokeStyle = "#2E303C";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx - 32, h * 0.62);
      ctx.lineTo(cx, h * 0.76);
      ctx.lineTo(cx + 32, h * 0.62);
      ctx.stroke();

      // Neck
      ctx.fillStyle = "#B98B72";
      ctx.fillRect(cx - 20, cy + 36, 40, 36);

      // Head portrait oval with directional key lighting
      const skinGrad = ctx.createRadialGradient(cx - 14, cy - 12, 8, cx, cy, 74);
      const rSkin = clamp(Math.round(218 * expFactor + hwBrightOffset), 40, 250);
      const gSkin = clamp(Math.round(172 * expFactor + hwBrightOffset), 30, 240);
      const bSkin = clamp(Math.round(144 * expFactor + hwBrightOffset), 25, 230);
      skinGrad.addColorStop(0, `rgb(${rSkin}, ${gSkin}, ${bSkin})`);
      skinGrad.addColorStop(
        1,
        `rgb(${Math.round(rSkin * 0.68)}, ${Math.round(gSkin * 0.66)}, ${Math.round(bSkin * 0.65)})`
      );
      ctx.fillStyle = skinGrad;
      ctx.beginPath();
      ctx.ellipse(cx, cy, 50, 66, 0, 0, Math.PI * 2);
      ctx.fill();

      // Hair / Brow contour
      ctx.fillStyle = "#181619";
      ctx.beginPath();
      ctx.ellipse(cx, cy - 42, 51, 28, 0, Math.PI, Math.PI * 2);
      ctx.fill();

      // Eyes & Glasses frame for optical sharpness reference
      ctx.strokeStyle = "#D4AF37";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(cx - 34, cy - 14, 26, 16);
      ctx.strokeRect(cx + 8, cy - 14, 26, 16);
      ctx.beginPath();
      ctx.moveTo(cx - 8, cy - 6);
      ctx.lineTo(cx + 8, cy - 6);
      ctx.stroke();

      // Colorchecker calibration strip in lower-left scene for LUT verification
      const swatches = ["#B93A32", "#E1A53C", "#4B9B55", "#2D87B9", "#7D5295", "#D8D8D8"];
      swatches.forEach((col, i) => {
        ctx.fillStyle = col;
        ctx.fillRect(28 + i * 20, h - 38, 17, 14);
      });
    };

    const renderLoop = (now: number) => {
      const dt = Math.max(1, now - lastTime);
      lastTime = now;
      frameIntervals.push(dt);
      if (frameIntervals.length > 30) frameIntervals.shift();
      const avgDt = frameIntervals.reduce((a, b) => a + b, 0) / frameIntervals.length;
      const p = paramsRef.current;
      const targetSensorFps = p.manual_exposure_lock ? 30.0 : 15.0;
      const jitter = Math.sin(now * 0.002) * 0.1;
      const liveFps = clamp(
        videoRef.current && videoRef.current.readyState >= 2
          ? 1000 / avgDt
          : targetSensorFps + jitter,
        14.8,
        30.0
      );

      if (Math.random() < 0.35) {
        onFpsUpdatedRef.current(liveFps);
      }

      const tSec = now * 0.001;

      // Update synthetic VU meter if no hardware mic is active
      if (!audioLevelRef.current.liveMic) {
        const wave =
          -24.0 +
          Math.sin(tSec * 4.3) * 8.5 +
          Math.cos(tSec * 9.7) * 5.2 +
          Math.sin(tSec * 1.9) * 4.0;
        audioLevelRef.current.rmsDb = clamp(wave, -60, -2);
        audioLevelRef.current.peakDb = Math.max(
          audioLevelRef.current.rmsDb + 3.5,
          audioLevelRef.current.peakDb - 0.25
        );
      }

      // Step Gimbal EMA
      const targetZoom = p.auto_framing ? p.subject_target_zoom : p.digital_zoom;
      const targetPanX = p.auto_framing ? Math.sin(tSec * 0.85) * 0.08 : p.pan_x;
      const targetPanY = p.auto_framing ? Math.cos(tSec * 0.6) * 0.04 : p.tilt_y;
      gimbalRef.current = stepGimbalEMA(
        gimbalRef.current,
        { zoom: targetZoom, panX: targetPanX, panY: targetPanY },
        p.gimbal_damping
      );

      const displayCanvas = displayCanvasRef.current;
      if (displayCanvas && procCtx) {
        const pw = procCanvas.width;
        const ph = procCanvas.height;

        procCtx.save();
        procCtx.clearRect(0, 0, pw, ph);

        // Apply Mirror H, Flip V, and PTZ crop transform
        procCtx.translate(pw * 0.5, ph * 0.5);
        const z = gimbalRef.current.zoom;
        procCtx.scale(
          (p.mirror_h ? -1 : 1) * z,
          (p.flip_v ? -1 : 1) * z
        );
        if (p.rotate_quadrant % 4 !== 0) {
          procCtx.rotate(((p.rotate_quadrant % 4) * Math.PI) / 2);
        }
        const maxPanPxX = (pw * (1 - 1 / z)) * 0.5;
        const maxPanPxY = (ph * (1 - 1 / z)) * 0.5;
        procCtx.translate(
          -pw * 0.5 - gimbalRef.current.panX * maxPanPxX,
          -ph * 0.5 - gimbalRef.current.panY * maxPanPxY
        );

        const videoEl = videoRef.current;
        if (videoEl && videoEl.readyState >= 2 && videoEl.videoWidth > 0) {
          procCtx.drawImage(videoEl, 0, 0, pw, ph);
        } else {
          drawSyntheticReferenceScene(procCtx, pw, ph, tSec, p);
        }
        procCtx.restore();

        // Pixel-level ISP Pipeline: AI Studio Lighting + 256x3 LUT + Vignette + Film Grain
        const imgData = procCtx.getImageData(0, 0, pw, ph);
        const data = imgData.data;
        const lut = build256LUT(p, customCubeRef.current);

        const aiMode = p.ai_mode;
        const dimFactor = 1.0 - clamp(p.spotlight_dim_pct / 100.0, 0, 0.95);
        const vigStrength = p.optical_vignette;
        const grainStrength = p.film_grain * 18.0;
        const satBoost =
          p.film_look === "Leica Monochrome" ? 0.0 : p.vibrance / 100.0;

        // Parse custom backdrop color
        const hexClean = p.backdrop_color_hex.replace("#", "");
        const bdR = parseInt(hexClean.slice(0, 2) || "12", 16) || 18;
        const bdG = parseInt(hexClean.slice(2, 4) || "12", 16) || 18;
        const bdB = parseInt(hexClean.slice(4, 6) || "16", 16) || 22;

        const subjCx = pw * 0.5 + Math.sin(tSec * 0.85) * 9;
        const subjCy = ph * 0.48;
        const rxInv = 1.0 / (pw * 0.24);
        const ryInv = 1.0 / (ph * 0.42);

        for (let y = 0; y < ph; y++) {
          const ny = (y - ph * 0.5) / (ph * 0.5);
          const dySubj = (y - subjCy) * ryInv;
          const rowOff = y * pw * 4;

          for (let x = 0; x < pw; x++) {
            const idx = rowOff + x * 4;
            let r = data[idx];
            let g = data[idx + 1];
            let b = data[idx + 2];

            // Stage 4: Dual-Engine Elliptical Subject Mask for Studio Spotlight / Backdrop / Bokeh
            if (aiMode !== "Off (Natural Scene)") {
              const dxSubj = (x - subjCx) * rxInv;
              const dist2 = dxSubj * dxSubj + dySubj * dySubj;
              const subjMask = clamp(Math.exp(-Math.pow(dist2, 1.45)), 0, 1);

              if (aiMode === "Studio Spotlight (Dim Background)") {
                const bgR = r * dimFactor * 0.94;
                const bgG = g * dimFactor;
                const bgB = b * dimFactor * 1.06;
                r = r * subjMask + bgR * (1 - subjMask);
                g = g * subjMask + bgG * (1 - subjMask);
                b = b * subjMask + bgB * (1 - subjMask);
              } else if (aiMode === "Custom Studio Backdrop" && !backdropImgRef.current) {
                r = r * subjMask + bdR * (1 - subjMask);
                g = g * subjMask + bdG * (1 - subjMask);
                b = b * subjMask + bdB * (1 - subjMask);
              } else if (aiMode === "Optical Bokeh Blur (DSLR Portrait)") {
                // Smooth peripheral defocus approximation
                const neighborIdx =
                  rowOff + clamp(x + ((x + y) % 5) - 2, 0, pw - 1) * 4;
                const br = (r + data[neighborIdx]) * 0.5 * 0.92;
                const bg = (g + data[neighborIdx + 1]) * 0.5 * 0.92;
                const bb = (b + data[neighborIdx + 2]) * 0.5 * 0.95;
                r = r * subjMask + br * (1 - subjMask);
                g = g * subjMask + bg * (1 - subjMask);
                b = b * subjMask + bb * (1 - subjMask);
              }
            }

            // Stage 6: 256x3 LUT Lookup
            r = lut.r[clamp(Math.round(r), 0, 255)];
            g = lut.g[clamp(Math.round(g), 0, 255)];
            b = lut.b[clamp(Math.round(b), 0, 255)];

            // Smart Vibrance
            if (Math.abs(satBoost) > 0.01) {
              const avg = (r + g + b) * 0.3333;
              const maxCh = Math.max(r, g, b);
              const minCh = Math.min(r, g, b);
              const curSat = (maxCh - minCh) / 255.0;
              const weight = (1.0 - curSat) * satBoost * 0.65;
              r += (r - avg) * weight;
              g += (g - avg) * weight;
              b += (b - avg) * weight;
            }

            // Stage 7: Radial Cosine-Fourth Optical Vignette & Organic Film Grain
            if (vigStrength > 0.005) {
              const nx = (x - pw * 0.5) / (pw * 0.5);
              const r2 = nx * nx + ny * ny;
              const vig = Math.max(0.15, 1.0 - vigStrength * 0.58 * r2);
              r *= vig;
              g *= vig;
              b *= vig;
            }

            if (grainStrength > 0.05) {
              const noise = (((x * 13 + y * 37 + Math.floor(now)) % 19) - 9) * 0.11 * grainStrength;
              r += noise;
              g += noise;
              b += noise;
            }

            data[idx] = clamp(r, 0, 255);
            data[idx + 1] = clamp(g, 0, 255);
            data[idx + 2] = clamp(b, 0, 255);
          }
        }

        // Compute 64-bin RGB + Luma Histogram
        const hist64 = computeHistogram64FromRGBA(data, pw, ph, 4);
        procCtx.putImageData(imgData, 0, 0);

        // Stage 9: Burn-in Broadcast Overlays onto processed frame (so snapshots include them)
        if (p.show_lower_third) {
          const cardX = 24;
          const cardH = 38;
          const cardY = ph - 28 - cardH;
          const cardW = 240;
          procCtx.fillStyle = "rgba(14, 14, 18, 0.86)";
          procCtx.fillRect(cardX, cardY, cardW, cardH);
          procCtx.strokeStyle = "#2C2C38";
          procCtx.lineWidth = 1;
          procCtx.strokeRect(cardX, cardY, cardW, cardH);

          const barCol = p.lower_third_accent.includes("Crimson")
            ? "#E11D48"
            : p.lower_third_accent.includes("Monochrome")
              ? "#F4F4F6"
              : "#E5A93C";
          procCtx.fillStyle = barCol;
          procCtx.fillRect(cardX, cardY, 3, cardH);

          procCtx.fillStyle = "#F4F4F6";
          procCtx.font = 'bold 11px "Plus Jakarta Sans", sans-serif';
          procCtx.fillText((p.lower_third_name || "ALEXANDER VANCE").slice(0, 32), cardX + 10, cardY + 16);

          procCtx.fillStyle = barCol;
          procCtx.font = '600 9px "JetBrains Mono", monospace';
          procCtx.fillText(
            (p.lower_third_role || "DIRECTOR OF PHOTOGRAPHY // LIVE").slice(0, 40),
            cardX + 10,
            cardY + 30
          );
        }

        if (p.show_watermark && watermarkImgRef.current) {
          procCtx.save();
          procCtx.globalAlpha = clamp(p.watermark_opacity / 100, 0.1, 1.0);
          const wmW = 72;
          const wmH = 28;
          const pad = 16;
          let wx = pw - wmW - pad;
          let wy = pad;
          if (p.watermark_position === "Top-Left") {
            wx = pad;
            wy = pad;
          } else if (p.watermark_position === "Bottom-Right") {
            wx = pw - wmW - pad;
            wy = ph - wmH - pad;
          } else if (p.watermark_position === "Bottom-Left") {
            wx = pad;
            wy = ph - wmH - pad;
          }
          procCtx.drawImage(watermarkImgRef.current, wx, wy, wmW, wmH);
          procCtx.restore();
        }

        if (p.burn_in_timecode) {
          const d = new Date();
          const isoDate = d.toISOString().slice(0, 10);
          const timePart = d.toTimeString().slice(0, 8);
          const ff = String(Math.floor((d.getMilliseconds() / 1000) * 30)).padStart(2, "0");
          const tcStr = `${isoDate}  ${timePart}:${ff}`;

          const bx = pw - 168;
          const by = ph - 32;
          procCtx.fillStyle = "rgba(10, 10, 13, 0.82)";
          procCtx.fillRect(bx, by, 154, 20);
          procCtx.strokeStyle = "#2C2C38";
          procCtx.strokeRect(bx, by, 154, 20);
          procCtx.fillStyle = "#E5A93C";
          procCtx.font = 'bold 9.5px "JetBrains Mono", monospace';
          procCtx.fillText(tcStr, bx + 7, by + 13.5);
        }

        // Check if a snapshot capture was requested
        if (captureRequestCounter !== lastCaptureProcessedRef.current) {
          lastCaptureProcessedRef.current = captureRequestCounter;
          const outW = p.upscale_1080p ? 1920 : 1280;
          const outH = p.upscale_1080p ? 1080 : 720;
          const dataUrl = procCanvas.toDataURL("image/png");
          onFrameCapturedRef.current(dataUrl, outW, outH);
        }

        // Render onto Display Canvas with OSD HUD Overlays
        const rect = displayCanvas.getBoundingClientRect();
        if (displayCanvas.width !== Math.floor(rect.width) || displayCanvas.height !== Math.floor(rect.height)) {
          displayCanvas.width = Math.max(320, Math.floor(rect.width));
          displayCanvas.height = Math.max(200, Math.floor(rect.height));
        }

        const dCtx = displayCanvas.getContext("2d");
        if (dCtx) {
          const cw = displayCanvas.width;
          const ch = displayCanvas.height;

          // Void Background #070709
          dCtx.fillStyle = "#070709";
          dCtx.fillRect(0, 0, cw, ch);

          // Fit 16:9 active video rectangle
          const pad = 14;
          const availW = Math.max(64, cw - pad * 2);
          const availH = Math.max(36, ch - pad * 2);
          let vw = availW;
          let vh = vw / (16 / 9);
          if (vh > availH) {
            vh = availH;
            vw = vh * (16 / 9);
          }
          const vx = (cw - vw) * 0.5;
          const vy = (ch - vh) * 0.5;

          dCtx.drawImage(procCanvas, vx, vy, vw, vh);

          // Composition Guide Overlays
          dCtx.save();
          dCtx.beginPath();
          dCtx.rect(vx, vy, vw, vh);
          dCtx.clip();

          // 2.35:1 Cinema Anamorphic Letterbox
          if (p.guide_anamorphic) {
            const targetH = vw / 2.35;
            if (targetH < vh) {
              const barH = (vh - targetH) * 0.5;
              dCtx.fillStyle = "rgba(0, 0, 0, 0.85)";
              dCtx.fillRect(vx, vy, vw, barH);
              dCtx.fillRect(vx, vy + vh - barH, vw, barH);
              dCtx.strokeStyle = "rgba(229, 169, 60, 0.55)";
              dCtx.lineWidth = 1;
              dCtx.beginPath();
              dCtx.moveTo(vx, vy + barH);
              dCtx.lineTo(vx + vw, vy + barH);
              dCtx.moveTo(vx, vy + vh - barH);
              dCtx.lineTo(vx + vw, vy + vh - barH);
              dCtx.stroke();
            }
          }

          // 9:16 Vertical Social Reel Guide
          if (p.guide_vertical_reel) {
            const reelW = vh * (9 / 16);
            if (reelW < vw) {
              const wingW = (vw - reelW) * 0.5;
              dCtx.fillStyle = "rgba(0, 0, 0, 0.65)";
              dCtx.fillRect(vx, vy, wingW, vh);
              dCtx.fillRect(vx + vw - wingW, vy, wingW, vh);
              dCtx.strokeStyle = "#E5A93C";
              dCtx.lineWidth = 1.2;
              dCtx.strokeRect(vx + wingW, vy, reelW, vh);
            }
          }

          // Rule of Thirds
          if (p.guide_thirds) {
            dCtx.strokeStyle = "rgba(255, 255, 255, 0.4)";
            dCtx.lineWidth = 1;
            dCtx.beginPath();
            for (const f of [1 / 3, 2 / 3]) {
              dCtx.moveTo(vx + vw * f, vy);
              dCtx.lineTo(vx + vw * f, vy + vh);
              dCtx.moveTo(vx, vy + vh * f);
              dCtx.lineTo(vx + vw, vy + vh * f);
            }
            dCtx.stroke();
          }

          // Golden Ratio (Phi 0.382 / 0.618)
          if (p.guide_golden) {
            dCtx.strokeStyle = "rgba(229, 169, 60, 0.53)";
            dCtx.lineWidth = 1;
            dCtx.beginPath();
            for (const f of [0.382, 0.618]) {
              dCtx.moveTo(vx + vw * f, vy);
              dCtx.lineTo(vx + vw * f, vy + vh);
              dCtx.moveTo(vx, vy + vh * f);
              dCtx.lineTo(vx + vw, vy + vh * f);
            }
            dCtx.stroke();
          }

          // Center Crosshair + Safe Action (90%) & Safe Title (80%)
          if (p.guide_crosshair_safe) {
            dCtx.save();
            dCtx.setLineDash([4, 4]);
            dCtx.strokeStyle = "rgba(255, 255, 255, 0.38)";
            dCtx.strokeRect(vx + vw * 0.05, vy + vh * 0.05, vw * 0.9, vh * 0.9);
            dCtx.strokeRect(vx + vw * 0.1, vy + vh * 0.1, vw * 0.8, vh * 0.8);
            dCtx.restore();

            const cx = vx + vw * 0.5;
            const cy = vy + vh * 0.5;
            dCtx.strokeStyle = "#E5A93C";
            dCtx.lineWidth = 1.2;
            dCtx.beginPath();
            dCtx.moveTo(cx - 24, cy);
            dCtx.lineTo(cx - 5, cy);
            dCtx.moveTo(cx + 5, cy);
            dCtx.lineTo(cx + 24, cy);
            dCtx.moveTo(cx, cy - 24);
            dCtx.lineTo(cx, cy - 5);
            dCtx.moveTo(cx, cy + 5);
            dCtx.lineTo(cx, cy + 24);
            dCtx.stroke();
          }
          dCtx.restore();

          // Dynamic 2px Tally Frame around active video rectangle
          dCtx.strokeStyle = isRecRef.current
            ? "#E11D48"
            : isVcamRef.current
              ? "#10B981"
              : "#262630";
          dCtx.lineWidth = 2;
          dCtx.strokeRect(vx, vy, vw, vh);

          // Top-Left Floating 64-Bin RGB + Luma Histogram Widget (x: 18, y: 18, w: 190, h: 95)
          if (p.show_histogram) {
            const hx = vx + 18;
            const hy = vy + 18;
            const hw = 190;
            const hh = 95;

            dCtx.fillStyle = "rgba(10, 10, 14, 0.78)";
            dCtx.strokeStyle = "rgba(255, 255, 255, 0.12)";
            dCtx.lineWidth = 1;
            dCtx.beginPath();
            dCtx.roundRect(hx, hy, hw, hh, 6);
            dCtx.fill();
            dCtx.stroke();

            dCtx.fillStyle = "#9CA3AF";
            dCtx.font = 'bold 9px "JetBrains Mono", monospace';
            dCtx.fillText("RGB // LUMA HISTOGRAM", hx + 8, hy + 14);

            const px0 = hx + 8;
            const py0 = hy + 20;
            const pwPlot = hw - 16;
            const phPlot = hh - 26;

            const channels: { arr: Float32Array; stroke: string; fill: string }[] = [
              { arr: hist64.b, stroke: "#0A84FF", fill: "rgba(10, 132, 255, 0.22)" },
              { arr: hist64.g, stroke: "#32D74B", fill: "rgba(50, 215, 75, 0.22)" },
              { arr: hist64.r, stroke: "#FF453A", fill: "rgba(255, 69, 58, 0.22)" },
              { arr: hist64.luma, stroke: "#F4F4F6", fill: "rgba(244, 244, 246, 0.18)" },
            ];

            for (const chObj of channels) {
              dCtx.beginPath();
              dCtx.moveTo(px0, py0 + phPlot);
              for (let i = 0; i < 64; i++) {
                const xPt = px0 + (i / 63) * pwPlot;
                const yPt = py0 + phPlot - chObj.arr[i] * phPlot;
                dCtx.lineTo(xPt, yPt);
              }
              dCtx.lineTo(px0 + pwPlot, py0 + phPlot);
              dCtx.closePath();
              dCtx.fillStyle = chObj.fill;
              dCtx.fill();

              dCtx.beginPath();
              for (let i = 0; i < 64; i++) {
                const xPt = px0 + (i / 63) * pwPlot;
                const yPt = py0 + phPlot - chObj.arr[i] * phPlot;
                if (i === 0) dCtx.moveTo(xPt, yPt);
                else dCtx.lineTo(xPt, yPt);
              }
              dCtx.strokeStyle = chObj.stroke;
              dCtx.lineWidth = 1.2;
              dCtx.stroke();
            }
          }

          // Top-Right PTZ Radar Box (w: 120, h: 68) when zoom > 1.01x or Auto-Framing active
          if (gimbalRef.current.zoom > 1.01 || p.auto_framing) {
            const rw = 120;
            const rh = 68;
            const rx = vx + vw - rw - 18;
            const ry = vy + 18;

            dCtx.fillStyle = "rgba(10, 10, 14, 0.78)";
            dCtx.strokeStyle = "rgba(255, 255, 255, 0.18)";
            dCtx.lineWidth = 1;
            dCtx.beginPath();
            dCtx.roundRect(rx, ry, rw, rh, 4);
            dCtx.fill();
            dCtx.stroke();

            const gz = Math.max(1.0, gimbalRef.current.zoom);
            const cropW = rw / gz;
            const cropH = rh / gz;
            const maxDx = (rw - cropW) * 0.5;
            const maxDy = (rh - cropH) * 0.5;
            const cx = rx + rw * 0.5 + gimbalRef.current.panX * maxDx;
            const cy = ry + rh * 0.5 + gimbalRef.current.panY * maxDy;

            dCtx.fillStyle = "rgba(229, 169, 60, 0.16)";
            dCtx.strokeStyle = "#E5A93C";
            dCtx.lineWidth = 1.5;
            dCtx.fillRect(cx - cropW * 0.5, cy - cropH * 0.5, cropW, cropH);
            dCtx.strokeRect(cx - cropW * 0.5, cy - cropH * 0.5, cropW, cropH);

            dCtx.fillStyle = "#E5A93C";
            dCtx.font = 'bold 9px "JetBrains Mono", monospace';
            dCtx.fillText(`PTZ ${gz.toFixed(2)}x`, rx + rw - 58, ry + rh - 5);
          }

          // Bottom-Left Audio Peak VU Meter (x: 18, bottom: 18, w: 230, h: 32)
          if (p.show_vu_meter) {
            const mw = 230;
            const mh = 32;
            const mx = vx + 18;
            const my = vy + vh - mh - 18;

            dCtx.fillStyle = "rgba(10, 10, 14, 0.78)";
            dCtx.strokeStyle = "rgba(255, 255, 255, 0.12)";
            dCtx.lineWidth = 1;
            dCtx.beginPath();
            dCtx.roundRect(mx, my, mw, mh, 6);
            dCtx.fill();
            dCtx.stroke();

            dCtx.fillStyle = "#9CA3AF";
            dCtx.font = 'bold 9px "JetBrains Mono", monospace';
            dCtx.fillText("MIC VU", mx + 8, my + 19);

            const bx = mx + 52;
            const bw = 122;
            const by1 = my + 10;
            const by2 = my + 18;
            const bh = 4.5;

            dCtx.fillStyle = "#22222B";
            dCtx.fillRect(bx, by1, bw, bh);
            dCtx.fillRect(bx, by2, bw, bh);

            const normRms = clamp((audioLevelRef.current.rmsDb + 60) / 60, 0, 1);
            const normPeak = clamp((audioLevelRef.current.peakDb + 60) / 60, 0, 1);

            const drawBar = (yPos: number, lvl: number) => {
              if (lvl <= 0.005) return;
              const gEnd = Math.min(lvl, 0.7);
              dCtx.fillStyle = "#10B981";
              dCtx.fillRect(bx, yPos, bw * gEnd, bh);
              if (lvl > 0.7) {
                const aEnd = Math.min(lvl, 0.9);
                dCtx.fillStyle = "#E5A93C";
                dCtx.fillRect(bx + bw * 0.7, yPos, bw * (aEnd - 0.7), bh);
              }
              if (lvl > 0.9) {
                dCtx.fillStyle = "#E11D48";
                dCtx.fillRect(bx + bw * 0.9, yPos, bw * (lvl - 0.9), bh);
              }
            };

            drawBar(by1, normRms);
            drawBar(by2, normRms * 0.96);

            // Peak-hold white tick mark
            if (normPeak > 0.02) {
              const pkX = bx + bw * normPeak;
              dCtx.strokeStyle = "#F4F4F6";
              dCtx.lineWidth = 1.5;
              dCtx.beginPath();
              dCtx.moveTo(pkX, by1 - 1);
              dCtx.lineTo(pkX, by2 + bh + 1);
              dCtx.stroke();
            }

            dCtx.fillStyle = "#E5A93C";
            dCtx.font = 'bold 9.5px "JetBrains Mono", monospace';
            dCtx.fillText(`${Math.round(audioLevelRef.current.rmsDb)}dB`, bx + bw + 6, my + 19);
          }

          // Countdown Timer Overlay
          if (countdownRef.current > 0) {
            const ccx = vx + vw * 0.5;
            const ccy = vy + vh * 0.5;
            dCtx.fillStyle = "rgba(10, 10, 13, 0.82)";
            dCtx.strokeStyle = "#E5A93C";
            dCtx.lineWidth = 3;
            dCtx.beginPath();
            dCtx.arc(ccx, ccy, 60, 0, Math.PI * 2);
            dCtx.fill();
            dCtx.stroke();

            dCtx.fillStyle = "#F4F4F6";
            dCtx.font = 'bold 56px "JetBrains Mono", monospace';
            dCtx.textAlign = "center";
            dCtx.textBaseline = "middle";
            dCtx.fillText(String(countdownRef.current), ccx, ccy + 2);
            dCtx.textAlign = "start";
            dCtx.textBaseline = "alphabetic";
          }

          // Softbox Screen Flash Overlay (#FFFDF8 for 280ms + smooth fade)
          if (flashHoldFramesRef.current > 0 || flashAlphaRef.current > 0.01) {
            if (flashHoldFramesRef.current > 0) {
              flashHoldFramesRef.current -= 1;
            } else {
              flashAlphaRef.current = Math.max(0, flashAlphaRef.current - 0.1);
            }
            dCtx.fillStyle = `rgba(255, 253, 248, ${flashAlphaRef.current.toFixed(3)})`;
            dCtx.fillRect(0, 0, cw, ch);
          }
        }
      }

      rafId = requestAnimationFrame(renderLoop);
    };

    rafId = requestAnimationFrame(renderLoop);
    return () => cancelAnimationFrame(rafId);
  }, [captureRequestCounter]);

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const step = e.deltaY < 0 ? 0.08 : -0.08;
    const nextZoom = clamp(Number((params.digital_zoom + step).toFixed(2)), 1.0, 3.0);
    const nextPanX = nextZoom <= 1.01 ? 0 : params.pan_x;
    const nextPanY = nextZoom <= 1.01 ? 0 : params.tilt_y;
    onPtzDragged(nextZoom, nextPanX, nextPanY);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button === 0 && params.digital_zoom > 1.01) {
      setDragging(true);
      dragLastPosRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!dragging || params.digital_zoom <= 1.01) return;
    const dx = (e.clientX - dragLastPosRef.current.x) / 220;
    const dy = (e.clientY - dragLastPosRef.current.y) / 160;
    dragLastPosRef.current = { x: e.clientX, y: e.clientY };
    onPtzDragged(
      params.digital_zoom,
      clamp(Number((params.pan_x - dx).toFixed(2)), -1.0, 1.0),
      clamp(Number((params.tilt_y - dy).toFixed(2)), -1.0, 1.0)
    );
  };

  const handleMouseUp = () => {
    if (dragging) setDragging(false);
  };

  return (
    <main
      className="flex-1 h-full relative flex items-center justify-center overflow-hidden"
      style={{ backgroundColor: "#070709" }}
    >
      <canvas
        ref={displayCanvasRef}
        data-testid="studio-viewport-canvas"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={onPtzReset}
        title="Scroll Wheel: Optical Zoom (±0.08x) | Drag when zoomed: Pan/Tilt | Double-Click: Reset PTZ"
        className="w-full h-full block"
        style={{
          cursor: dragging
            ? "grabbing"
            : params.digital_zoom > 1.01
              ? "grab"
              : "default",
        }}
      />
    </main>
  );
};
