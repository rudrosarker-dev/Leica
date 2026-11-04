export type StudioLookName =
  | 'Natural (Off)'
  | 'Warm Studio'
  | 'Clean Daylight'
  | 'Soft Portrait'
  | 'Cinema Teal'
  | 'Classic B&W';

export const STUDIO_LOOK_NAMES: StudioLookName[] = [
  'Natural (Off)',
  'Warm Studio',
  'Clean Daylight',
  'Soft Portrait',
  'Cinema Teal',
  'Classic B&W',
];

export type BackgroundMode =
  | 'Off (Natural Background)'
  | 'Subtle Studio Spotlight'
  | 'Soft Bokeh Blur'
  | 'Custom Backdrop';

export interface StudioParams {
  // Pure View Bypass
  pure_view_bypass: boolean;

  // Tab 1: Light
  auto_exposure: boolean;
  manual_exposure: boolean;
  exposure_ev: number; // -11 to -2
  smart_light_boost: number; // 0 to 100 (Dark Room Lift)
  hw_brightness: number; // 0 to 255 (128 = neutral)
  hw_contrast: number; // 0 to 255 (128 = neutral)
  s_curve: number; // 0 to 100 (Highlight Roll-Off / Tone Curve)
  hw_sharpness: number; // 0 to 255 (128 = neutral)
  clarity: number; // 0 to 100
  denoise: number; // 0 to 100

  // Tab 2: Color
  active_lut: StudioLookName;
  lut_intensity: number; // 0 to 100
  auto_wb: boolean;
  wb_kelvin: number; // 2800 to 6500
  temp_shift: number; // -50 to +50 (Warmth)
  tint: number; // -50 to +50 (Tint)
  hw_saturation: number; // 0 to 255 (128 = neutral)
  vibrance: number; // -50 to +50
  lift: number; // -25 to +25
  gamma: number; // 50 to 150 (100 = 1.00 neutral)
  gain: number; // -25 to +25

  // Tab 3: Frame
  zoom: number; // 100 to 300 (100 = 1.0x)
  pan_x: number; // -100 to +100
  tilt_y: number; // -100 to +100
  mirror_h: boolean;
  flip_v: boolean;
  rotation_deg: 0 | 90 | 180 | 270;
  ai_auto_frame: boolean;
  bg_mode: BackgroundMode;
  bokeh_strength: number; // 5 to 45
  spotlight_dim: number; // 0 to 85
  vignette: number; // 0 to 100
  grain: number; // 0 to 100

  // Tab 4: Studio
  active_preset_name: string;
  show_grid: boolean;
  show_cinema_bars: boolean;
  show_corner_hud: boolean;
  upscale_1080p: boolean;
  virtual_cam_active: boolean;
  timer_sec: 0 | 3 | 5 | 10;
  screen_flash: boolean;
  hw_gain: number;
  powerline_hz: 'Off' | '50 Hz' | '60 Hz';
}

/**
 * 100% Pure Sensor Passthrough Default State:
 * Guarantees crystal-clear 30.0 FPS natural video on launch with zero dark exposure or color blotches.
 */
export const DEFAULT_STUDIO_PARAMS: StudioParams = {
  pure_view_bypass: false,

  // Tab 1: Light (100% Pure Sensor Passthrough)
  auto_exposure: true,
  manual_exposure: false,
  exposure_ev: -5,
  smart_light_boost: 0,
  hw_brightness: 128,
  hw_contrast: 128,
  s_curve: 0,
  hw_sharpness: 128,
  clarity: 0,
  denoise: 0,

  // Tab 2: Color (100% Neutral Natural Color)
  active_lut: 'Natural (Off)',
  lut_intensity: 75,
  auto_wb: true,
  wb_kelvin: 5000,
  temp_shift: 0,
  tint: 0,
  hw_saturation: 128,
  vibrance: 0,
  lift: 0,
  gamma: 100,
  gain: 0,

  // Tab 3: Frame (1.0x Full Sensor, Background Off)
  zoom: 100,
  pan_x: 0,
  tilt_y: 0,
  mirror_h: true,
  flip_v: false,
  rotation_deg: 0,
  ai_auto_frame: false,
  bg_mode: 'Off (Natural Background)',
  bokeh_strength: 21,
  spotlight_dim: 35,
  vignette: 0,
  grain: 0,

  // Tab 4: Studio (Clean Unobstructed Viewport)
  active_preset_name: 'Default (Pure Natural)',
  show_grid: false,
  show_cinema_bars: false,
  show_corner_hud: false,
  upscale_1080p: false,
  virtual_cam_active: false,
  timer_sec: 0,
  screen_flash: false,
  hw_gain: 64,
  powerline_hz: '60 Hz',
};

export const FACTORY_PRESETS: Record<string, Partial<StudioParams>> = {
  'Default (Pure Natural)': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: 'Default (Pure Natural)',
  },
  'Bright Meeting HD': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: 'Bright Meeting HD',
    smart_light_boost: 32,
    s_curve: 18,
    clarity: 15,
    active_lut: 'Clean Daylight',
    lut_intensity: 65,
    temp_shift: 4,
  },
  'Warm Creator Look': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: 'Warm Creator Look',
    smart_light_boost: 22,
    s_curve: 28,
    clarity: 18,
    active_lut: 'Warm Studio',
    lut_intensity: 75,
    temp_shift: 10,
    vibrance: 12,
    bg_mode: 'Subtle Studio Spotlight',
    spotlight_dim: 30,
  },
  'Monochrome Film': {
    ...DEFAULT_STUDIO_PARAMS,
    active_preset_name: 'Monochrome Film',
    smart_light_boost: 18,
    s_curve: 35,
    clarity: 24,
    active_lut: 'Classic B&W',
    lut_intensity: 100,
    vignette: 18,
  },
};

export function clampByte(val: number): number {
  if (val <= 0) return 0;
  if (val >= 255) return 255;
  return Math.round(val);
}

/**
 * Fast-path check: returns true if all color & light controls are at their neutral passthrough values.
 */
export function isColorAndLightNeutral(params: StudioParams): boolean {
  if (params.pure_view_bypass) return true;
  const lutOff =
    params.active_lut === 'Natural (Off)' || params.lut_intensity <= 0;
  return (
    lutOff &&
    params.smart_light_boost === 0 &&
    params.hw_brightness === 128 &&
    params.hw_contrast === 128 &&
    params.hw_saturation === 128 &&
    params.s_curve === 0 &&
    params.temp_shift === 0 &&
    params.tint === 0 &&
    params.vibrance === 0 &&
    params.lift === 0 &&
    params.gamma === 100 &&
    params.gain === 0
  );
}

/**
 * Generates 3x256 RGB 1D Lookup Tables:
 * - Smart Light Boost shadow curve: x = x ** (1.0 / (1.0 + boost * 0.8))
 * - Smooth midtone-weighted channel shifts (Math.sin(x * Math.PI)) so pure black (0)
 *   and pure white (255) NEVER shift red or green.
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
  const boostPower = 1.0 / (1.0 + boostNorm * 0.8);

  const brOffset = ((params.hw_brightness - 128) / 128) * 0.18;
  const ctFactor = 1.0 + ((params.hw_contrast - 128) / 128) * 0.45;
  const liftNorm = (params.lift / 100) * 0.35;
  const gainNorm = (params.gain / 100) * 0.35;
  const gammaVal = Math.max(0.3, Math.min(2.8, params.gamma / 100));
  const invGamma = 1.0 / gammaVal;
  const sStrength = Math.max(0, Math.min(1, params.s_curve / 100));
  const lutAlpha = Math.max(0, Math.min(1, params.lut_intensity / 100));

  for (let i = 0; i < 256; i++) {
    let x = i / 255.0;

    // 1. Smart Light Boost (Dark Room Shadow Lift)
    if (boostNorm > 0.001) {
      x = Math.pow(Math.max(x, 0), boostPower);
    }

    // 2. Brightness & Contrast
    if (Math.abs(brOffset) > 0.001 || Math.abs(ctFactor - 1.0) > 0.001) {
      x = (x - 0.5) * ctFactor + 0.5 + brOffset;
      x = Math.max(0, Math.min(1, x));
    }

    // 3. Lift / Gamma / Gain
    if (
      Math.abs(liftNorm) > 0.001 ||
      Math.abs(gainNorm) > 0.001 ||
      Math.abs(gammaVal - 1.0) > 0.005
    ) {
      const lifted = x * (1.0 + gainNorm - liftNorm) + liftNorm;
      const clamped = Math.max(0.0001, Math.min(1.0, lifted));
      x = Math.pow(clamped, invGamma);
    }

    // 4. Highlight Roll-Off (S-Curve)
    if (sStrength > 0.001) {
      const k = 1.0 + sStrength * 4.2;
      const sig = 1.0 / (1.0 + Math.exp(-k * (x - 0.5)));
      const sig0 = 1.0 / (1.0 + Math.exp(-k * -0.5));
      const sig1 = 1.0 / (1.0 + Math.exp(-k * 0.5));
      const sigNorm = (sig - sig0) / Math.max(sig1 - sig0, 1e-6);
      x = (1.0 - sStrength) * x + sStrength * sigNorm;
    }

    // 5. Luminance-weighted Warmth & Tint (Math.sin(x * Math.PI) guarantees 0 shift at black=0 and white=1)
    const midWeight = Math.sin(Math.max(0, Math.min(1, x)) * Math.PI);
    const tempNorm = (params.temp_shift / 100) * 0.14;
    const tintNorm = (params.tint / 100) * 0.12;

    let r = x + tempNorm * midWeight - tintNorm * 0.35 * midWeight;
    let g = x + tintNorm * midWeight;
    let b = x - tempNorm * midWeight - tintNorm * 0.35 * midWeight;

    // 6. Studio Look Profile (Luminance-Weighted)
    if (params.active_lut !== 'Natural (Off)' && lutAlpha > 0.001) {
      const mw = Math.sin(Math.max(0, Math.min(1, x)) * Math.PI);
      const shadowEnv = Math.sin(Math.pow(Math.max(0, Math.min(1, x)), 0.7) * Math.PI);
      const highEnv = Math.sin(Math.pow(Math.max(0, Math.min(1, x)), 1.4) * Math.PI);

      let lr = r;
      let lg = g;
      let lb = b;

      switch (params.active_lut) {
        case 'Warm Studio':
          lr = Math.pow(Math.max(r, 0), 0.95) + 0.03 * mw;
          lg = Math.pow(Math.max(g, 0), 0.98) + 0.01 * mw;
          lb = Math.pow(Math.max(b, 0), 1.03) - 0.025 * mw;
          break;
        case 'Clean Daylight': {
          const base = Math.pow(Math.max(x, 0), 0.94);
          lr = base + (r - x) + 0.01 * highEnv;
          lg = base + (g - x) + 0.012 * mw;
          lb = base + (b - x) + 0.022 * mw;
          break;
        }
        case 'Soft Portrait': {
          const base = Math.pow(Math.max(x, 0), 0.92);
          lr = base + (r - x) + 0.025 * mw;
          lg = base + (g - x) + 0.008 * mw;
          lb = base + (b - x) - 0.012 * mw;
          break;
        }
        case 'Cinema Teal':
          lr = r + 0.045 * highEnv - 0.015 * shadowEnv;
          lg = g + 0.01 * mw;
          lb = b + 0.038 * shadowEnv - 0.025 * highEnv;
          break;
        case 'Classic B&W': {
          const bw = 1.0 / (1.0 + Math.exp(-4.8 * (x - 0.49)));
          const bw0 = 1.0 / (1.0 + Math.exp(-4.8 * -0.49));
          const bw1 = 1.0 / (1.0 + Math.exp(-4.8 * 0.51));
          const bwNorm = (bw - bw0) / Math.max(bw1 - bw0, 1e-6);
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

/**
 * Computes the centered crop rectangle for digital PTZ zoom & pan/tilt.
 */
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

/**
 * Computes real-time 64-bin RGB + Luminance histograms from an RGBA pixel buffer.
 */
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
