import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  C270_NATIVE_HARDWARE_DEFAULTS,
  DEFAULT_STUDIO_PARAMS,
  FACTORY_PRESETS,
  STUDIO_LOOK_NAMES,
  buildColorGradingLUTs,
  computePTZCropRect,
  computeRGBHistogram64,
  computeWallClockCFRFramesToWrite,
  isColorAndLightNeutral,
} from './ispMath';

describe('LUMIXA PRO // C270 CINEMA STUDIO — Hardware, CFR Recorder & ISP Math', () => {
  it('enforces exact Logitech C270 native DirectShow hardware defaults (Contrast=32, Saturation=32, Sharpness=24, Brightness=128)', () => {
    assert.equal(C270_NATIVE_HARDWARE_DEFAULTS.hw_brightness, 128);
    assert.equal(C270_NATIVE_HARDWARE_DEFAULTS.hw_contrast, 32);
    assert.equal(C270_NATIVE_HARDWARE_DEFAULTS.hw_saturation, 32);
    assert.equal(C270_NATIVE_HARDWARE_DEFAULTS.hw_sharpness, 24);
    assert.equal(C270_NATIVE_HARDWARE_DEFAULTS.hw_gain, 100);
    assert.equal(C270_NATIVE_HARDWARE_DEFAULTS.hw_backlight, 0);
    assert.equal(C270_NATIVE_HARDWARE_DEFAULTS.exposure_ev, -4);

    assert.equal(DEFAULT_STUDIO_PARAMS.unlock_30fps, true);
    assert.equal(DEFAULT_STUDIO_PARAMS.smart_light_boost, 25);
    assert.equal(DEFAULT_STUDIO_PARAMS.hw_contrast, 32);
    assert.equal(DEFAULT_STUDIO_PARAMS.hw_saturation, 32);
    assert.equal(DEFAULT_STUDIO_PARAMS.hw_sharpness, 24);
  });

  it('paces Wall-Clock CFR (30.0 FPS) video recording so 10.0s real time always equals 300 frames (1.0x speed)', () => {
    const step1 = computeWallClockCFRFramesToWrite(10.0, 0.0, 0, 30.0);
    assert.equal(step1.targetFrameIndex, 300);
    assert.equal(step1.framesToWriteNow, 300);

    // With 2.5 seconds paused during a 12.5-second wall-clock span -> 10.0s active -> 300 frames
    const stepPaused = computeWallClockCFRFramesToWrite(12.5, 2.5, 298, 30.0);
    assert.equal(stepPaused.targetFrameIndex, 300);
    assert.equal(stepPaused.framesToWriteNow, 2);
  });

  it('returns identity LUT when Pure View Bypass or neutral parameters are set', () => {
    const neutral = {
      ...DEFAULT_STUDIO_PARAMS,
      smart_light_boost: 0,
    };
    assert.equal(isColorAndLightNeutral(neutral), true);
    const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(neutral);
    for (let i = 0; i < 256; i++) {
      assert.equal(rLUT[i], i);
      assert.equal(gLUT[i], i);
      assert.equal(bLUT[i], i);
    }
  });

  it('weights all 8 Cinema Film Looks and Warmth/Tint by luminance so pure black (0) and pure white (255) never blotch', () => {
    assert.equal(STUDIO_LOOK_NAMES.length, 8);
    for (const look of STUDIO_LOOK_NAMES) {
      const graded = {
        ...DEFAULT_STUDIO_PARAMS,
        active_lut: look,
        lut_intensity: 100,
        temp_shift: 25,
        tint: -15,
      };
      const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(graded);
      assert.equal(rLUT[0], 0, `Black floor shifted on ${look}`);
      assert.equal(gLUT[0], 0, `Black floor shifted on ${look}`);
      assert.equal(bLUT[0], 0, `Black floor shifted on ${look}`);
      assert.equal(rLUT[255], 255, `White point clipped on ${look}`);
      assert.equal(gLUT[255], 255, `White point clipped on ${look}`);
      assert.equal(bLUT[255], 255, `White point clipped on ${look}`);
    }
  });

  it('verifies all 12 built-in studio presets exist and build valid 256-entry LUTs', () => {
    const keys = Object.keys(FACTORY_PRESETS);
    assert.equal(keys.length, 12);
    for (const name of keys) {
      const merged = { ...DEFAULT_STUDIO_PARAMS, ...FACTORY_PRESETS[name] };
      const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(merged);
      assert.equal(rLUT.length, 256);
      assert.equal(gLUT.length, 256);
      assert.equal(bLUT.length, 256);
    }
  });

  it('computes accurate PTZ crop bounds and 64-bin RGB histograms', () => {
    const zoom2x = computePTZCropRect(1280, 720, 200, 0, 0);
    assert.deepEqual(zoom2x, { x: 320, y: 180, width: 640, height: 360 });

    const buffer = new Uint8ClampedArray(64 * 4);
    for (let i = 0; i < buffer.length; i += 4) {
      buffer[i] = 200;
      buffer[i + 1] = 150;
      buffer[i + 2] = 100;
      buffer[i + 3] = 255;
    }
    const hist = computeRGBHistogram64(buffer, 1);
    assert.equal(hist.r.length, 64);
    assert.ok(hist.r[200 >> 2] > 0);
  });
});
