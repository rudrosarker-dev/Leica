export type StudioLookName =
  | 'Pure Natural (Off)'
  | 'Warm Studio'
  | 'Clean Daylight'
  | 'Kodak Portra'
  | 'Cinema Teal/Amber'
  | 'Soft Peach Skin'
  | 'Matte Obsidian'
  | 'Leica B&W';

export const STUDIO_LOOK_NAMES: StudioLookName[] = [
  'Pure Natural (Off)',
  'Warm Studio',
  'Clean Daylight',
  'Kodak Portra',
  'Cinema Teal/Amber',
  'Soft Peach Skin',
  'Matte Obsidian',
  'Leica B&W',
];

export type BackgroundMode =
  | 'Off (Natural)'
  | 'Optical Bokeh Blur'
  | 'Studio Dimmed Spotlight'
  | 'Custom Backdrop';

export interface StudioParams {
  // Master Bypass
  pure_view_bypass: boolean;
  active_preset_name: string;

  // MODE 1: 1. EXPOSURE & LIGHT
  // Card 1: Lighting & Clarity
  smart_light_boost: number; // 0 to 100%, Default: 25% when 30-FPS Boost is ON
  digital_brightness: number; // -100 to +100, Default: 0
  micro_contrast: number; // -100 to +100, Default: 0
  optical_sharpness: number; // 0 to 100%, Default: 15%
  denoise: number; // 0 to 100%, Default: 0%

  // Card 2: C270 Sensor Hardware — Exact Native Ranges
  unlock_30fps: boolean; // Default: true (Disables C270 Low-Light Lag: Backlight=0, AutoExp=0.25, Exp=-4 EV)
  exposure_ev: number; // -11 to -2 EV, Default: -4 EV
  hw_gain: number; // 0 to 255 ISO, Default: 130 (Native factory default = 100)
  hw_brightness: number; // 0 to 255, Native Default = 128
  hw_contrast: number; // 0 to 255, Native Default = 32 (CRITICAL: never 135!)
  hw_saturation: number; // 0 to 255, Native Default = 32 (CRITICAL: never 132!)
  hw_sharpness: number; // 0 to 255, Native Default = 24 (CRITICAL: never 140!)
  hw_backlight: 0 | 1 | 2; // 0 = OFF (30 FPS Fast), 1 = ON (10 FPS Slow)
  powerline_hz: '50 Hz' | '60 Hz' | 'Off';
  auto_wb: boolean;

  // MODE 2: 2. COLOR & LUTS
  active_lut: StudioLookName;
  lut_intensity: number; // 0 to 100%, Default: 75%
  custom_cube_name: string;
  temp_shift: number; // -100 Cool to +100 Warm, Default: 0
  tint: number; // -100 to +100, Default: 0
  vibrance: number; // -100 to +100, Default: 0
  vignette: number; // 0 to 100%, Default: 0%

  // MODE 3: 3. OPTICS & AI
  zoom: number; // 100 to 300 (100 = 1.00x, 300 = 3.00x)
  pan_x: number; // -100 to +100 (-1.00 to +1.00)
  tilt_y: number; // -100 to +100 (-1.00 to +1.00)
  mirror_h: boolean; // Default: true
  flip_v: boolean; // Default: false
  rotation_deg: 0 | 90 | 180 | 270;
  aspect_mode: '16:9' | '9:16';
  bg_mode: BackgroundMode;
  bg_strength: number; // 10 to 100%, Default: 50%
  ai_auto_frame: boolean; // AI Face Auto-Framing (Center Stage)
  skin_softening: number; // 0 to 100%, Default: 0%
  show_grid: boolean;
  show_cinema_bars: boolean;
  show_corner_hud: boolean;
  show_lower_third: boolean;
  lower_third_name: string;
  lower_third_title: string;

  // MODE 4: 4. PRESETS (12) & OUTPUT
  upscale_1080p: boolean;
  virtual_cam_active: boolean;
  timer_sec: 0 | 3 | 5 | 10;
  screen_flash: boolean;
}

/**
 * Exact Native Logitech C270 Hardware Factory Defaults (DirectShow Video Proc Amp & Camera Control)
 */
export const C270_NATIVE_HARDWARE_DEFAULTS = {
  hw_brightness: 128,
  hw_contrast: 32,
  hw_saturation: 32,
  hw_sharpness: 24,
  hw_gain: 100,
  hw_backlight: 0 as const,
  exposure_ev: -4,
  powerline_hz: '50 Hz' as const,
  auto_wb: true,
};

export const C270_NATIVE_HW_DEFAULTS = C270_NATIVE_HARDWARE_DEFAULTS;

export function apply30FpsAntiLagBoost(
  prev: StudioParams,
  enabled: boolean
): StudioParams {
  if (enabled) {
    return {
      ...prev,
      unlock_30fps: true,
      hw_backlight: 0,
      exposure_ev: -4,
      hw_gain: Math.max(prev.hw_gain, 130),
      smart_light_boost: Math.max(prev.smart_light_boost, 25),
    };
  }
  return {
    ...prev,
    unlock_30fps: false,
    hw_backlight: 1,
  };
}

export function restoreNativeC270DriverDefaults(
  prev: StudioParams
): StudioParams {
  return {
    ...prev,
    ...C270_NATIVE_HARDWARE_DEFAULTS,
  };
}

export const DEFAULT_STUDIO_PARAMS: StudioParams = {
  pure_view_bypass: false,
  active_preset_name: '01. Pure Natural 30FPS',

  // Mode 1: Exposure & Light
  smart_light_boost: 25,
  digital_brightness: 0,
  micro_contrast: 0,
  optical_sharpness: 15,
  denoise: 0,

  unlock_30fps: true,
  exposure_ev: -4,
  hw_gain: 130,
  hw_brightness: 128,
  hw_contrast: 32,
  hw_saturation: 32,
  hw_sharpness: 24,
  hw_backlight: 0,
  powerline_hz: '50 Hz',
  auto_wb: true,

  // Mode 2: Color & LUTs
  active_lut: 'Pure Natural (Off)',
  lut_intensity: 75,
  custom_cube_name: '',
  temp_shift: 0,
  tint: 0,
  vibrance: 0,
  vignette: 0,

  // Mode 3: Optics & AI
  zoom: 100,
  pan_x: 0,
  tilt_y: 0,
  mirror_h: true,
  flip_v: false,
  rotation_deg: 0,
  aspect_mode: '16:9',
  bg_mode: 'Off (Natural)',
  bg_strength: 50,
  ai_auto_frame: false,
  skin_softening: 0,
  show_grid: false,
  show_cinema_bars: false,
  show_corner_hud: false,
  show_lower_third: false,
  lower_third_name: 'Alex Morgan',
  lower_third_title: 'Cinema Systems Architect',

  // Mode 4: Presets & Output
  upscale_1080p: false,
  virtual_cam_active: false,
  timer_sec: 0,
  screen_flash: false,
};

export const PRESET_DESCRIPTIONS: Record<string, string> = {
  '01. Pure Natural 30FPS': 'Clean 30FPS with natural light',
  '02. Dark Room Bright 30FPS': 'High shadow lift + gain for dim bedrooms at 30FPS',
  '03. Pro Zoom / Meet HD': 'Crisp sharpness, balanced skin tone, subtle spotlight',
  '04. YouTube Creator Warm': 'Warm tungsten key light feel, rich contrast, bokeh',
  '05. Podcast Moody Studio': 'Dimmed background spotlight 55%, warm skin, vignette',
  '06. Daylight Window Fix': 'Balanced highlight roll-off for bright windows',
  '07. Kodak Portra Film': 'Golden vintage analog film look',
  '08. Cinema Anamorphic': 'Teal & Amber grade + 2.35:1 cinema widescreen bars',
  '09. Portrait DSLR Bokeh': 'Soft skin retouch + deep optical background blur',
  '10. Leica Monochrome B&W': 'High-contrast silver-halide black & white',
  '11. Neon Cyber Night': 'Cool shadows, vibrant highlights, crisp edges',
  '12. Broadcast News Clean': 'High clarity, neutral white balance, lower-third active',
};

export const FACTORY_PRESETS: Record<string, Partial<StudioParams>> = {
  '01. Pure Natural 30FPS': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '01. Pure Natural 30FPS',
    unlock_30fps: true,
    smart_light_boost: 25,
    optical_sharpness: 15,
    active_lut: 'Pure Natural (Off)',
  },
  '02. Dark Room Bright 30FPS': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '02. Dark Room Bright 30FPS',
    unlock_30fps: true,
    smart_light_boost: 58,
    digital_brightness: 12,
    micro_contrast: 8,
    optical_sharpness: 20,
    denoise: 22,
    exposure_ev: -4,
    hw_gain: 165,
    active_lut: 'Warm Studio',
    lut_intensity: 55,
  },
  '03. Pro Zoom / Meet HD': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '03. Pro Zoom / Meet HD',
    unlock_30fps: true,
    smart_light_boost: 28,
    digital_brightness: 4,
    micro_contrast: 10,
    optical_sharpness: 28,
    denoise: 12,
    active_lut: 'Clean Daylight',
    lut_intensity: 65,
    temp_shift: 4,
    vibrance: 8,
    bg_mode: 'Studio Dimmed Spotlight',
    bg_strength: 35,
  },
  '04. YouTube Creator Warm': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '04. YouTube Creator Warm',
    unlock_30fps: true,
    smart_light_boost: 30,
    micro_contrast: 16,
    optical_sharpness: 24,
    active_lut: 'Warm Studio',
    lut_intensity: 80,
    temp_shift: 14,
    vibrance: 14,
    vignette: 15,
    bg_mode: 'Optical Bokeh Blur',
    bg_strength: 55,
  },
  '05. Podcast Moody Studio': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '05. Podcast Moody Studio',
    unlock_30fps: true,
    smart_light_boost: 18,
    micro_contrast: 22,
    optical_sharpness: 20,
    active_lut: 'Matte Obsidian',
    lut_intensity: 80,
    temp_shift: 10,
    vignette: 32,
    bg_mode: 'Studio Dimmed Spotlight',
    bg_strength: 55,
  },
  '06. Daylight Window Fix': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '06. Daylight Window Fix',
    unlock_30fps: true,
    smart_light_boost: 14,
    digital_brightness: -6,
    micro_contrast: 12,
    optical_sharpness: 18,
    exposure_ev: -5,
    hw_gain: 105,
    active_lut: 'Clean Daylight',
    lut_intensity: 70,
    temp_shift: -6,
  },
  '07. Kodak Portra Film': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '07. Kodak Portra Film',
    unlock_30fps: true,
    smart_light_boost: 26,
    micro_contrast: 14,
    optical_sharpness: 12,
    active_lut: 'Kodak Portra',
    lut_intensity: 85,
    temp_shift: 12,
    vibrance: 10,
    vignette: 20,
  },
  '08. Cinema Anamorphic': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '08. Cinema Anamorphic',
    unlock_30fps: true,
    smart_light_boost: 24,
    micro_contrast: 20,
    optical_sharpness: 22,
    active_lut: 'Cinema Teal/Amber',
    lut_intensity: 88,
    vibrance: 12,
    vignette: 24,
    show_cinema_bars: true,
  },
  '09. Portrait DSLR Bokeh': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '09. Portrait DSLR Bokeh',
    unlock_30fps: true,
    smart_light_boost: 28,
    micro_contrast: 8,
    optical_sharpness: 16,
    active_lut: 'Soft Peach Skin',
    lut_intensity: 75,
    temp_shift: 8,
    skin_softening: 45,
    bg_mode: 'Optical Bokeh Blur',
    bg_strength: 75,
  },
  '10. Leica Monochrome B&W': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '10. Leica Monochrome B&W',
    unlock_30fps: true,
    smart_light_boost: 22,
    micro_contrast: 28,
    optical_sharpness: 32,
    active_lut: 'Leica B&W',
    lut_intensity: 100,
    vignette: 28,
  },
  '11. Neon Cyber Night': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '11. Neon Cyber Night',
    unlock_30fps: true,
    smart_light_boost: 32,
    micro_contrast: 24,
    optical_sharpness: 30,
    active_lut: 'Cinema Teal/Amber',
    lut_intensity: 92,
    temp_shift: -18,
    tint: 22,
    vibrance: 26,
    vignette: 22,
  },
  '12. Broadcast News Clean': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: '12. Broadcast News Clean',
    unlock_30fps: true,
    smart_light_boost: 28,
    micro_contrast: 14,
    optical_sharpness: 34,
    denoise: 10,
    active_lut: 'Clean Daylight',
    lut_intensity: 70,
    vibrance: 6,
    show_lower_third: true,
  },
};

export function clampByte(val: number): number {
  if (val <= 0) return 0;
  if (val >= 255) return 255;
  return Math.round(val);
}

/**
 * Wall-Clock CFR (Constant Frame Rate 30.0 FPS) Pacer Calculation:
 * Guarantees that `elapsedSeconds` of real-world recording always writes `int(elapsedSeconds * targetFps)`
 * frames so a 10-second capture NEVER plays back at 3x fast-forward speed.
 */
export function computeWallClockCFRFramesToWrite(
  elapsedSeconds: number,
  pausedSeconds: number,
  framesWrittenSoFar: number,
  targetFps: number = 30.0
): { targetFrameIndex: number; framesToWriteNow: number } {
  const activeElapsed = Math.max(0, elapsedSeconds - pausedSeconds);
  const targetFrameIndex = Math.floor(activeElapsed * targetFps);
  const framesToWriteNow = Math.max(0, targetFrameIndex - framesWrittenSoFar);
  return { targetFrameIndex, framesToWriteNow };
}

export function isColorAndLightNeutral(params: StudioParams): boolean {
  if (params.pure_view_bypass) return true;
  const lutOff =
    params.active_lut === 'Pure Natural (Off)' || params.lut_intensity <= 0;
  return (
    lutOff &&
    params.smart_light_boost === 0 &&
    params.digital_brightness === 0 &&
    params.micro_contrast === 0 &&
    params.hw_brightness === 128 &&
    params.hw_contrast === 32 &&
    params.hw_saturation === 32 &&
    params.temp_shift === 0 &&
    params.tint === 0 &&
    params.vibrance === 0
  );
}

/**
 * Generates 3x256 RGB 1D Lookup Tables for all 8 Cinema Film Looks, Smart Room Light Boost,
 * Digital Brightness, Micro-Contrast, Hardware Proc Amp offsets, and Luminance-Weighted Warmth/Tint.
 */
export function buildColorGradingLUTs(params: StudioParams): {
  rLUT: Uint8Array;
  gLUT: Uint8Array;
  bLUT: Uint8Array;
} {
  const rLUT = new Uint8Array(256);
  const gLUT = new Uint8Array(256);
  const bLUT = new Uint8Array(256);

  if (isColorAndLightNeutral(params)) {
    for (let i = 0; i < 256; i++) {
      rLUT[i] = i;
      gLUT[i] = i;
      bLUT[i] = i;
    }
    return { rLUT, gLUT, bLUT };
  }

  const boostNorm = Math.max(0, Math.min(1, params.smart_light_boost / 100));
  const boostPower = 1.0 / (1.0 + boostNorm * 0.85);

  const hwBrOffset = ((params.hw_brightness - 128) / 128) * 0.18;
  const hwCtFactor = 1.0 + ((params.hw_contrast - 32) / 128) * 0.45;
  const digBrNorm = params.digital_brightness / 100.0;
  const microCtNorm = params.micro_contrast / 100.0;
  const lutAlpha = Math.max(0, Math.min(1, params.lut_intensity / 100));

  for (let i = 0; i < 256; i++) {
    let x = i / 255.0;

    // 1. Smart Room Light Boost (Zero-Latency Shadow Lift for 30-FPS Boost)
    if (boostNorm > 0.001) {
      x = Math.pow(Math.max(x, 0), boostPower);
    }

    // 2. Digital Brightness (midtone-weighted so black floor stays clean)
    if (Math.abs(digBrNorm) > 0.001) {
      x = Math.max(
        0,
        Math.min(1, x + digBrNorm * 0.26 * Math.sin(x * Math.PI))
      );
    }

    // 3. Hardware Brightness & Contrast Proc Amp
    if (Math.abs(hwBrOffset) > 0.001 || Math.abs(hwCtFactor - 1.0) > 0.001) {
      const midEnv = Math.sin(x * Math.PI);
      x = (x - 0.5) * hwCtFactor + 0.5 + hwBrOffset * midEnv;
      x = Math.max(0, Math.min(1, x));
    }

    // 4. Micro-Contrast S-Curve
    if (Math.abs(microCtNorm) > 0.001) {
      if (microCtNorm > 0) {
        const k = 3.5 + microCtNorm * 5.0;
        const sig = 1.0 / (1.0 + Math.exp(-k * (x - 0.5)));
        const s0 = 1.0 / (1.0 + Math.exp(-k * -0.5));
        const s1 = 1.0 / (1.0 + Math.exp(-k * 0.5));
        const sigNorm = (sig - s0) / Math.max(s1 - s0, 1e-6);
        x = (1.0 - microCtNorm * 0.65) * x + microCtNorm * 0.65 * sigNorm;
      } else {
        x = Math.max(
          0,
          Math.min(1, 0.5 + (x - 0.5) * (1.0 + microCtNorm * 0.45))
        );
      }
    }

    // 5. Luminance-weighted Warmth & Tint (Math.sin(x * Math.PI) guarantees 0 shift at black=0 and white=1)
    const midWeight = Math.sin(Math.max(0, Math.min(1, x)) * Math.PI);
    const tempNorm = (params.temp_shift / 100) * 0.12;
    const tintNorm = (params.tint / 100) * 0.1;

    let r = Math.max(0, Math.min(1, x + (tempNorm + tintNorm * 0.25) * midWeight));
    let g = Math.max(0, Math.min(1, x - tintNorm * 0.85 * midWeight));
    let b = Math.max(0, Math.min(1, x + (-tempNorm + tintNorm * 0.25) * midWeight));

    // 6. 8 Cinema Film Look Profiles (Luminance-Weighted)
    if (params.active_lut !== 'Pure Natural (Off)' && lutAlpha > 0.001) {
      const mw = Math.sin(Math.max(0, Math.min(1, x)) * Math.PI);
      const lowMid = mw * (1.0 - x);
      const highMid = mw * x;

      let lr = r;
      let lg = g;
      let lb = b;

      switch (params.active_lut) {
        case 'Warm Studio': {
          const lifted = Math.pow(x, 0.93);
          lr = Math.min(1, Math.max(0, lifted + (r - x) + 0.042 * mw));
          lg = Math.min(1, Math.max(0, lifted + (g - x) + 0.014 * mw));
          lb = Math.min(1, Math.max(0, lifted + (b - x) - 0.034 * mw));
          break;
        }
        case 'Clean Daylight': {
          const base = x * 0.96 + 0.04 * Math.pow(x, 0.88);
          lr = Math.min(1, Math.max(0, base + (r - x) - 0.012 * mw));
          lg = Math.min(1, Math.max(0, base + (g - x) + 0.008 * mw));
          lb = Math.min(1, Math.max(0, base + (b - x) + 0.028 * mw));
          break;
        }
        case 'Kodak Portra': {
          const film = Math.pow(x, 0.91) + 0.018 * mw;
          lr = Math.min(1, Math.max(0, film + (r - x) + 0.046 * mw));
          lg = Math.min(1, Math.max(0, film + (g - x) + 0.018 * mw));
          lb = Math.min(1, Math.max(0, film + (b - x) - 0.028 * mw));
          break;
        }
        case 'Cinema Teal/Amber': {
          lr = Math.min(1, Math.max(0, r - 0.038 * lowMid + 0.054 * highMid));
          lg = Math.min(1, Math.max(0, g + 0.018 * lowMid + 0.014 * highMid));
          lb = Math.min(1, Math.max(0, b + 0.048 * lowMid - 0.042 * highMid));
          break;
        }
        case 'Soft Peach Skin': {
          const soft = Math.pow(x, 0.92) + 0.015 * mw;
          lr = Math.min(1, Math.max(0, soft + (r - x) + 0.032 * mw));
          lg = Math.min(1, Math.max(0, soft + (g - x) + 0.012 * mw));
          lb = Math.min(1, Math.max(0, soft + (b - x) - 0.014 * mw));
          break;
        }
        case 'Matte Obsidian': {
          const matte = 0.04 * mw + Math.pow(x, 0.96) * 0.96;
          const sig = 1.0 / (1.0 + Math.exp(-4.2 * (matte - 0.5)));
          const s0 = 1.0 / (1.0 + Math.exp(-4.2 * -0.5));
          const s1 = 1.0 / (1.0 + Math.exp(-4.2 * 0.5));
          const norm = Math.max(0, Math.min(1, (sig - s0) / (s1 - s0)));
          lr = Math.min(1, Math.max(0, norm + 0.015 * mw));
          lg = Math.min(1, Math.max(0, norm + 0.005 * mw));
          lb = Math.min(1, Math.max(0, norm - 0.01 * mw));
          break;
        }
        case 'Leica B&W': {
          const bw = 1.0 / (1.0 + Math.exp(-5.4 * (x - 0.5)));
          const bw0 = 1.0 / (1.0 + Math.exp(-5.4 * -0.5));
          const bw1 = 1.0 / (1.0 + Math.exp(-5.4 * 0.5));
          const bwNorm = Math.max(0, Math.min(1, (bw - bw0) / (bw1 - bw0)));
          lr = bwNorm;
          lg = bwNorm;
          lb = bwNorm;
          break;
        }
      }

      r = (1.0 - lutAlpha) * r + lutAlpha * lr;
      g = (1.0 - lutAlpha) * g + lutAlpha * lg;
      b = (1.0 - lutAlpha) * b + lutAlpha * lb;
    }

    rLUT[i] = clampByte(r * 255);
    gLUT[i] = clampByte(g * 255);
    bLUT[i] = clampByte(b * 255);
  }

  return { rLUT, gLUT, bLUT };
}

export function computePTZCropRect(
  frameWidth: number,
  frameHeight: number,
  zoomPct: number,
  panX: number,
  tiltY: number
): { x: number; y: number; width: number; height: number } {
  const zoom = Math.max(1.0, Math.min(3.0, zoomPct / 100.0));
  const cropW = Math.max(64, Math.min(frameWidth, Math.round(frameWidth / zoom)));
  const cropH = Math.max(36, Math.min(frameHeight, Math.round(frameHeight / zoom)));

  const maxOffsetX = (frameWidth - cropW) / 2.0;
  const maxOffsetY = (frameHeight - cropH) / 2.0;

  const cx = frameWidth / 2.0 + (panX / 100.0) * maxOffsetX;
  const cy = frameHeight / 2.0 + (tiltY / 100.0) * maxOffsetY;

  const x = Math.max(0, Math.min(frameWidth - cropW, Math.round(cx - cropW / 2.0)));
  const y = Math.max(0, Math.min(frameHeight - cropH, Math.round(cy - cropH / 2.0)));

  return { x, y, width: cropW, height: cropH };
}

export function computeRGBHistogram64(
  rgbaData: Uint8ClampedArray,
  sampleStep: number = 16
): { r: number[]; g: number[]; b: number[]; luma: number[] } {
  const r = new Array<number>(64).fill(0);
  const g = new Array<number>(64).fill(0);
  const b = new Array<number>(64).fill(0);
  const luma = new Array<number>(64).fill(0);

  const step = Math.max(1, sampleStep) * 4;
  let count = 0;

  for (let i = 0; i < rgbaData.length; i += step) {
    const rv = rgbaData[i];
    const gv = rgbaData[i + 1];
    const bv = rgbaData[i + 2];
    const lv = (rv * 77 + gv * 150 + bv * 29) >> 8;

    r[rv >> 2]++;
    g[gv >> 2]++;
    b[bv >> 2]++;
    luma[lv >> 2]++;
    count++;
  }

  if (count > 0) {
    const scale = 100 / (count * 0.12);
    for (let j = 0; j < 64; j++) {
      r[j] = Math.min(100, Math.round(r[j] * scale));
      g[j] = Math.min(100, Math.round(g[j] * scale));
      b[j] = Math.min(100, Math.round(b[j] * scale));
      luma[j] = Math.min(100, Math.round(luma[j] * scale));
    }
  }

  return { r, g, b, luma };
}
