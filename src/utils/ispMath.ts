/**
 * Pure Mathematical ISP, 1D/3D LUT Color Grading, .CUBE Parser, Gimbal EMA PTZ,
 * and 64-Bin RGB/Luma Histogram Engine for LEICA // C270 OPTIX STUDIO.
 * Mirrors the exact mathematical pipeline of `core/color_lut.py`, `core/camera_engine.py`,
 * and `core/preset_manager.py`.
 */

export type FilmLookName =
  | "Rec.709 Neutral"
  | "Kodak Portra 400"
  | "Leica Monochrome"
  | "Teal & Orange"
  | "Matte Obsidian"
  | "Warm Tungsten";

export const FILM_LOOK_NAMES: FilmLookName[] = [
  "Rec.709 Neutral",
  "Kodak Portra 400",
  "Leica Monochrome",
  "Teal & Orange",
  "Matte Obsidian",
  "Warm Tungsten",
];

export type AIStudioMode =
  | "Off (Natural Scene)"
  | "Studio Spotlight (Dim Background)"
  | "Optical Bokeh Blur (DSLR Portrait)"
  | "Custom Studio Backdrop";

export interface StudioParams {
  // Zone B - Card 1: C270 30-FPS Hardware Engine
  manual_exposure_lock: boolean;
  anti_flicker_50hz: boolean;
  hardware_exposure: number;
  hardware_gain: number;
  backlight_comp: number;

  // Zone B - Card 2: Sensor Color & White Balance
  auto_wb: boolean;
  wb_kelvin: number;
  hardware_brightness: number;
  hardware_contrast: number;
  hardware_saturation: number;
  hardware_sharpness: number;

  // Zone B - Card 3: Optical ISP & Super-Resolution
  upscale_1080p: boolean;
  optical_clarity: number;
  denoise_strength: number;
  edge_detail_radius: number;

  // Zone B - Card 4: Fluid PTZ & Geometry
  digital_zoom: number;
  pan_x: number;
  tilt_y: number;
  mirror_h: boolean;
  flip_v: boolean;
  rotate_quadrant: number;

  // Zone D - Tab 1: Color & LUT
  film_look: FilmLookName;
  custom_cube_name: string;
  lut_intensity: number;
  temp_shift: number;
  tint_shift: number;
  shadows_lift: number;
  midtones_gamma: number;
  highlights_gain: number;
  scurve_contrast: number;
  vibrance: number;
  optical_vignette: number;
  film_grain: number;

  // Zone D - Tab 2: AI Studio
  ai_mode: AIStudioMode;
  spotlight_dim_pct: number;
  bokeh_blur_radius: number;
  edge_feather: number;
  backdrop_color_hex: string;
  auto_framing: boolean;
  subject_target_zoom: number;
  gimbal_damping: number;
  skin_smoothing: number;

  // Zone D - Tab 3: Overlays
  show_histogram: boolean;
  show_vu_meter: boolean;
  guide_thirds: boolean;
  guide_golden: boolean;
  guide_crosshair_safe: boolean;
  guide_anamorphic: boolean;
  guide_vertical_reel: boolean;
  show_lower_third: boolean;
  lower_third_name: string;
  lower_third_role: string;
  lower_third_accent: string;
  show_watermark: boolean;
  watermark_position: "Top-Right" | "Top-Left" | "Bottom-Right" | "Bottom-Left";
  watermark_opacity: number;
  burn_in_timecode: boolean;
}

export const DEFAULT_STUDIO_PARAMS: StudioParams = {
  manual_exposure_lock: true,
  anti_flicker_50hz: true,
  hardware_exposure: -5,
  hardware_gain: 110,
  backlight_comp: 0,

  auto_wb: true,
  wb_kelvin: 5000,
  hardware_brightness: 128,
  hardware_contrast: 135,
  hardware_saturation: 132,
  hardware_sharpness: 140,

  upscale_1080p: false,
  optical_clarity: 0.8,
  denoise_strength: 0.15,
  edge_detail_radius: 1.0,

  digital_zoom: 1.0,
  pan_x: 0.0,
  tilt_y: 0.0,
  mirror_h: true,
  flip_v: false,
  rotate_quadrant: 0,

  film_look: "Kodak Portra 400",
  custom_cube_name: "",
  lut_intensity: 100,
  temp_shift: 0,
  tint_shift: 0,
  shadows_lift: 0,
  midtones_gamma: 1.0,
  highlights_gain: 0,
  scurve_contrast: 0.15,
  vibrance: 15,
  optical_vignette: 0.15,
  film_grain: 0.0,

  ai_mode: "Studio Spotlight (Dim Background)",
  spotlight_dim_pct: 45,
  bokeh_blur_radius: 25,
  edge_feather: 7,
  backdrop_color_hex: "#121216",
  auto_framing: false,
  subject_target_zoom: 1.35,
  gimbal_damping: 0.08,
  skin_smoothing: 0.0,

  show_histogram: true,
  show_vu_meter: true,
  guide_thirds: false,
  guide_golden: false,
  guide_crosshair_safe: false,
  guide_anamorphic: false,
  guide_vertical_reel: false,
  show_lower_third: false,
  lower_third_name: "ALEXANDER VANCE",
  lower_third_role: "DIRECTOR OF PHOTOGRAPHY // LIVE",
  lower_third_accent: "Leica Amber (#E5A93C)",
  show_watermark: false,
  watermark_position: "Top-Right",
  watermark_opacity: 80,
  burn_in_timecode: false,
};

export const FACTORY_PRESETS: Record<string, StudioParams> = {
  "1. C270 30FPS Low-Light Fix": {
    ...DEFAULT_STUDIO_PARAMS,
    manual_exposure_lock: true,
    anti_flicker_50hz: true,
    hardware_exposure: -5,
    hardware_gain: 115,
    auto_wb: false,
    wb_kelvin: 4800,
    denoise_strength: 0.3,
    optical_clarity: 0.9,
    film_look: "Rec.709 Neutral",
    lut_intensity: 100,
    shadows_lift: 4,
    midtones_gamma: 1.08,
    highlights_gain: -4,
    scurve_contrast: 0.18,
    vibrance: 14,
    ai_mode: "Studio Spotlight (Dim Background)",
    spotlight_dim_pct: 40,
  },
  "2. Warm Aesthetic Portrait": {
    ...DEFAULT_STUDIO_PARAMS,
    manual_exposure_lock: true,
    hardware_exposure: -5,
    hardware_gain: 105,
    auto_wb: false,
    wb_kelvin: 5300,
    optical_clarity: 0.65,
    denoise_strength: 0.2,
    film_look: "Kodak Portra 400",
    lut_intensity: 92,
    temp_shift: 12,
    tint_shift: 4,
    shadows_lift: 3,
    midtones_gamma: 1.04,
    highlights_gain: -6,
    scurve_contrast: 0.2,
    vibrance: 18,
    optical_vignette: 0.22,
    film_grain: 0.08,
    ai_mode: "Optical Bokeh Blur (DSLR Portrait)",
    bokeh_blur_radius: 31,
    skin_smoothing: 0.3,
  },
  "3. Crisp 1080p Broadcast": {
    ...DEFAULT_STUDIO_PARAMS,
    manual_exposure_lock: true,
    hardware_exposure: -5,
    hardware_gain: 100,
    upscale_1080p: true,
    optical_clarity: 1.15,
    denoise_strength: 0.15,
    edge_detail_radius: 0.9,
    film_look: "Teal & Orange",
    lut_intensity: 75,
    scurve_contrast: 0.22,
    vibrance: 20,
    optical_vignette: 0.12,
    ai_mode: "Studio Spotlight (Dim Background)",
    spotlight_dim_pct: 50,
    show_lower_third: true,
  },
  "4. Leica Monochrome Studio": {
    ...DEFAULT_STUDIO_PARAMS,
    manual_exposure_lock: true,
    hardware_exposure: -6,
    hardware_gain: 95,
    optical_clarity: 1.25,
    denoise_strength: 0.1,
    film_look: "Leica Monochrome",
    lut_intensity: 100,
    shadows_lift: -6,
    midtones_gamma: 0.96,
    highlights_gain: 8,
    scurve_contrast: 0.34,
    vibrance: 0,
    optical_vignette: 0.32,
    film_grain: 0.22,
    ai_mode: "Studio Spotlight (Dim Background)",
    spotlight_dim_pct: 65,
  },
};

export function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

export function getFpsBadgeColor(fps: number): string {
  if (fps >= 27.5) return "#10B981"; // Studio Emerald
  if (fps >= 18.0) return "#F59E0B"; // Warning Amber
  return "#E11D48"; // Cinema Crimson Red
}

export function formatMasterTimecode(totalFrames: number, fps = 30): string {
  const safeFps = Math.max(1, Math.round(fps));
  const totalSec = Math.floor(totalFrames / safeFps);
  const ff = totalFrames % safeFps;
  const hh = Math.floor(totalSec / 3600);
  const mm = Math.floor((totalSec % 3600) / 60);
  const ss = totalSec % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}:${pad(ff)}`;
}

export function stepGimbalEMA(
  current: { zoom: number; panX: number; panY: number },
  target: { zoom: number; panX: number; panY: number },
  damping: number
): { zoom: number; panX: number; panY: number } {
  const d = clamp(damping, 0.01, 1.0);
  return {
    zoom: clamp(current.zoom + (target.zoom - current.zoom) * d, 1.0, 3.0),
    panX: clamp(current.panX + (target.panX - current.panX) * d, -1.0, 1.0),
    panY: clamp(current.panY + (target.panY - current.panY) * d, -1.0, 1.0),
  };
}

export interface RGB1DLUT {
  r: Uint8Array;
  g: Uint8Array;
  b: Uint8Array;
}

export function applyFilmLookPoint(
  r: number,
  g: number,
  b: number,
  filmLook: FilmLookName
): [number, number, number] {
  if (filmLook === "Kodak Portra 400") {
    const rOut = clamp(
      Math.pow(r, 0.94) * 0.94 + (6.0 / 255.0) * (1.0 - r) + 0.015 * Math.sin(r * Math.PI),
      0.0,
      0.96
    );
    const gOut = clamp(
      Math.pow(g, 0.97) * 0.95 + (3.0 / 255.0) * (1.0 - g) + 0.008 * Math.sin(g * Math.PI),
      0.0,
      0.96
    );
    const bOut = clamp(Math.pow(b, 1.04) * 0.96 - (4.0 / 255.0) * (1.0 - b), 0.0, 0.95);
    return [rOut, gOut, bOut];
  }

  if (filmLook === "Leica Monochrome") {
    const luma = 0.25 * r + 0.65 * g + 0.1 * b;
    const sig = 1.0 / (1.0 + Math.exp(-7.2 * (luma - 0.48)));
    const sigMin = 1.0 / (1.0 + Math.exp(-7.2 * (0.0 - 0.48)));
    const sigMax = 1.0 / (1.0 + Math.exp(-7.2 * (1.0 - 0.48)));
    const sigNorm = (sig - sigMin) / (sigMax - sigMin);
    const floor = 8.0 / 255.0;
    const mono = clamp(floor + (1.0 - floor) * sigNorm, 0.0, 1.0);
    return [mono, mono, mono];
  }

  if (filmLook === "Teal & Orange") {
    const shadowWeight = clamp(1.0 - r * 1.8, 0.0, 1.0);
    const highWeight = clamp((r - 0.35) * 1.5, 0.0, 1.0);
    const rOut = clamp(r + (-10.0 / 255.0) * shadowWeight + (12.0 / 255.0) * highWeight, 0.0, 1.0);
    const gOut = clamp(g + (6.0 / 255.0) * shadowWeight + (4.0 / 255.0) * highWeight, 0.0, 1.0);
    const bOut = clamp(b + (14.0 / 255.0) * shadowWeight + (-10.0 / 255.0) * highWeight, 0.0, 1.0);
    return [rOut, gOut, bOut];
  }

  if (filmLook === "Matte Obsidian") {
    const rOut = clamp(0.06 + 0.88 * Math.pow(r, 1.16), 0.0, 0.95);
    const gOut = clamp(0.06 + 0.87 * Math.pow(g, 1.18), 0.0, 0.94);
    const bOut = clamp(0.068 + 0.89 * Math.pow(b, 1.14), 0.0, 0.96);
    return [rOut, gOut, bOut];
  }

  if (filmLook === "Warm Tungsten") {
    const rOut = clamp(Math.pow(r, 0.92) + (14.0 / 255.0) * (1.0 - 0.5 * r), 0.0, 0.98);
    const gOut = clamp(Math.pow(g, 0.97) + (5.0 / 255.0) * (1.0 - 0.5 * g), 0.0, 0.98);
    const bOut = clamp(Math.pow(b, 1.08) - (16.0 / 255.0) * (1.0 - 0.3 * b), 0.0, 0.96);
    return [rOut, gOut, bOut];
  }

  return [r, g, b];
}

export function build256LUT(
  params: StudioParams,
  custom1DLut?: { r: Float32Array; g: Float32Array; b: Float32Array } | null
): RGB1DLUT {
  const rTable = new Uint8Array(256);
  const gTable = new Uint8Array(256);
  const bTable = new Uint8Array(256);

  const lift = params.shadows_lift;
  const gamma = Math.max(0.2, params.midtones_gamma);
  const gain = params.highlights_gain;
  const contrast = params.scurve_contrast;
  const temp = params.temp_shift;
  const tint = params.tint_shift;
  const lutMix = clamp(params.lut_intensity / 100.0, 0.0, 1.0);
  const kelvinShift = params.auto_wb ? 0.0 : (params.wb_kelvin - 5000.0) / 65.0;

  const rOffset = (temp * 0.4 + kelvinShift * 0.35) / 255.0;
  const bOffset = (-temp * 0.4 - kelvinShift * 0.35) / 255.0;
  const gOffset = (-tint * 0.35) / 255.0;

  const k = 4.0 + contrast * 8.0;
  const sig0 = 1.0 / (1.0 + Math.exp(-k * -0.5));
  const sig1 = 1.0 / (1.0 + Math.exp(-k * 0.5));

  for (let i = 0; i < 256; i++) {
    const x = i / 255.0;
    let base = clamp(x * (1.0 + gain / 100.0 - lift / 100.0) + lift / 100.0, 0.0, 1.0);
    base = Math.pow(base, 1.0 / gamma);

    if (contrast > 0.001) {
      const sig = 1.0 / (1.0 + Math.exp(-k * (base - 0.5)));
      const sigNorm = (sig - sig0) / (sig1 - sig0);
      base = (1.0 - contrast) * base + contrast * sigNorm;
    }

    const r = clamp(base + rOffset, 0.0, 1.0);
    const g = clamp(base + gOffset, 0.0, 1.0);
    const b = clamp(base + bOffset, 0.0, 1.0);

    let rLook: number;
    let gLook: number;
    let bLook: number;

    if (custom1DLut) {
      const ir = clamp(Math.round(r * 255), 0, 255);
      const ig = clamp(Math.round(g * 255), 0, 255);
      const ib = clamp(Math.round(b * 255), 0, 255);
      rLook = custom1DLut.r[ir];
      gLook = custom1DLut.g[ig];
      bLook = custom1DLut.b[ib];
    } else {
      [rLook, gLook, bLook] = applyFilmLookPoint(r, g, b, params.film_look);
    }

    const rf = clamp((1.0 - lutMix) * r + lutMix * rLook, 0.0, 1.0);
    const gf = clamp((1.0 - lutMix) * g + lutMix * gLook, 0.0, 1.0);
    const bf = clamp((1.0 - lutMix) * b + lutMix * bLook, 0.0, 1.0);

    rTable[i] = Math.round(rf * 255);
    gTable[i] = Math.round(gf * 255);
    bTable[i] = Math.round(bf * 255);
  }

  return { r: rTable, g: gTable, b: bTable };
}

export function parseCubeLUTText(text: string): {
  valid: boolean;
  r: Float32Array;
  g: Float32Array;
  b: Float32Array;
  message: string;
} {
  const rows: [number, number, number][] = [];
  let size3d = 0;
  let size1d = 0;

  const lines = text.split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const upper = line.toUpperCase();
    if (upper.startsWith("TITLE") || upper.startsWith("DOMAIN_")) continue;
    if (upper.startsWith("LUT_3D_SIZE")) {
      const parts = line.split(/\s+/);
      if (parts.length >= 2) size3d = parseInt(parts[1], 10) || 0;
      continue;
    }
    if (upper.startsWith("LUT_1D_SIZE")) {
      const parts = line.split(/\s+/);
      if (parts.length >= 2) size1d = parseInt(parts[1], 10) || 0;
      continue;
    }
    const parts = line.split(/\s+/);
    if (parts.length === 3) {
      const rv = parseFloat(parts[0]);
      const gv = parseFloat(parts[1]);
      const bv = parseFloat(parts[2]);
      if (!Number.isNaN(rv) && !Number.isNaN(gv) && !Number.isNaN(bv)) {
        rows.push([clamp(rv, 0, 1), clamp(gv, 0, 1), clamp(bv, 0, 1)]);
      }
    }
  }

  const rOut = new Float32Array(256);
  const gOut = new Float32Array(256);
  const bOut = new Float32Array(256);

  if (size3d > 1 && rows.length === size3d * size3d * size3d) {
    // Extract diagonal neutral axis + color response onto 256 table
    for (let i = 0; i < 256; i++) {
      const pos = (i / 255) * (size3d - 1);
      const idx = Math.min(size3d - 1, Math.round(pos));
      const flatIdx = idx + idx * size3d + idx * size3d * size3d;
      const [rv, gv, bv] = rows[flatIdx] ?? [i / 255, i / 255, i / 255];
      rOut[i] = rv;
      gOut[i] = gv;
      bOut[i] = bv;
    }
    return {
      valid: true,
      r: rOut,
      g: gOut,
      b: bOut,
      message: `Loaded 3D .CUBE (${size3d}³)`,
    };
  }

  if (rows.length >= 2) {
    const n = size1d > 1 && rows.length >= size1d ? size1d : rows.length;
    for (let i = 0; i < 256; i++) {
      const pos = (i / 255) * (n - 1);
      const i0 = Math.floor(pos);
      const i1 = Math.min(n - 1, i0 + 1);
      const frac = pos - i0;
      rOut[i] = rows[i0][0] * (1 - frac) + rows[i1][0] * frac;
      gOut[i] = rows[i0][1] * (1 - frac) + rows[i1][1] * frac;
      bOut[i] = rows[i0][2] * (1 - frac) + rows[i1][2] * frac;
    }
    return {
      valid: true,
      r: rOut,
      g: gOut,
      b: bOut,
      message: `Loaded 1D .CUBE (${n} pts)`,
    };
  }

  return {
    valid: false,
    r: rOut,
    g: gOut,
    b: bOut,
    message: "Invalid .CUBE LUT file format",
  };
}

export interface Histogram64 {
  r: Float32Array;
  g: Float32Array;
  b: Float32Array;
  luma: Float32Array;
}

export function computeHistogram64FromRGBA(
  rgba: Uint8ClampedArray,
  width: number,
  height: number,
  step = 4
): Histogram64 {
  const rBins = new Float32Array(64);
  const gBins = new Float32Array(64);
  const bBins = new Float32Array(64);
  const yBins = new Float32Array(64);

  const stride = Math.max(1, step);
  for (let y = 0; y < height; y += stride) {
    const rowOffset = y * width * 4;
    for (let x = 0; x < width; x += stride) {
      const idx = rowOffset + x * 4;
      const rv = rgba[idx];
      const gv = rgba[idx + 1];
      const bv = rgba[idx + 2];
      const yv = (77 * rv + 150 * gv + 29 * bv) >> 8;

      rBins[rv >> 2] += 1;
      gBins[gv >> 2] += 1;
      bBins[bv >> 2] += 1;
      yBins[yv >> 2] += 1;
    }
  }

  const normalize = (arr: Float32Array) => {
    let maxVal = 0;
    for (let i = 0; i < 64; i++) {
      if (arr[i] > maxVal) maxVal = arr[i];
    }
    if (maxVal > 0) {
      for (let i = 0; i < 64; i++) {
        arr[i] = arr[i] / maxVal;
      }
    }
    return arr;
  };

  return {
    r: normalize(rBins),
    g: normalize(gBins),
    b: normalize(bBins),
    luma: normalize(yBins),
  };
}
