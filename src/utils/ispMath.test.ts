import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_STUDIO_PARAMS,
  FACTORY_PRESETS,
  buildColorGradingLUTs,
  computePTZCropRect,
  computeRGBHistogram64,
  isColorAndLightNeutral,
} from './ispMath.ts';

describe('Optix Studio V2 ISP Mathematical Pipeline', () => {
  it('defaults to 100% Pure Sensor Passthrough on startup (Auto Exposure, Natural Off, Bg Off)', () => {
    assert.equal(DEFAULT_STUDIO_PARAMS.auto_exposure, true);
    assert.equal(DEFAULT_STUDIO_PARAMS.manual_exposure, false);
    assert.equal(DEFAULT_STUDIO_PARAMS.active_lut, 'Natural (Off)');
    assert.equal(DEFAULT_STUDIO_PARAMS.bg_mode, 'Off (Natural Background)');
    assert.equal(DEFAULT_STUDIO_PARAMS.upscale_1080p, false);
    assert.equal(DEFAULT_STUDIO_PARAMS.smart_light_boost, 0);
    assert.equal(isColorAndLightNeutral(DEFAULT_STUDIO_PARAMS), true);

    const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(DEFAULT_STUDIO_PARAMS);
    for (let i = 0; i < 256; i++) {
      assert.equal(rLUT[i], i);
      assert.equal(gLUT[i], i);
      assert.equal(bLUT[i], i);
    }
  });

  it('brightens dark shadows cleanly with Smart Light Boost without blowing out pure white (255)', () => {
    const boosted = {
      ...DEFAULT_STUDIO_PARAMS,
      smart_light_boost: 60,
    };
    const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(boosted);
    assert.equal(rLUT[0], 0);
    assert.equal(rLUT[255], 255);
    // Dark shadow pixel (e.g. 40) is significantly lifted
    assert.ok(rLUT[40] > 70, `Expected shadow pixel 40 to lift above 70, got ${rLUT[40]}`);
    assert.equal(rLUT[40], gLUT[40]);
    assert.equal(gLUT[40], bLUT[40]);
  });

  it('weights Warmth, Tint, and Studio Looks by luminance so pure black (0) and pure white (255) never tint red or green', () => {
    const warmLook = {
      ...DEFAULT_STUDIO_PARAMS,
      active_lut: 'Warm Studio' as const,
      lut_intensity: 100,
      temp_shift: 35,
      tint: -25,
    };
    const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(warmLook);
    // Pure black stays 0,0,0 — zero red/green blotches in shadows
    assert.equal(rLUT[0], 0);
    assert.equal(gLUT[0], 0);
    assert.equal(bLUT[0], 0);
    // Pure white stays 255,255,255
    assert.equal(rLUT[255], 255);
    assert.equal(gLUT[255], 255);
    assert.equal(bLUT[255], 255);
    // Midtones receive warm golden shift (Red > Blue)
    assert.ok(rLUT[128] > bLUT[128]);
  });

  it('computes accurate PTZ crop bounds within 1280x720 sensor geometry', () => {
    const full = computePTZCropRect(1280, 720, 100, 0, 0);
    assert.deepEqual(full, { x: 0, y: 0, width: 1280, height: 720 });

    const zoom2x = computePTZCropRect(1280, 720, 200, 0, 0);
    assert.equal(zoom2x.width, 640);
    assert.equal(zoom2x.height, 360);
    assert.equal(zoom2x.x, 320);
    assert.equal(zoom2x.y, 180);
  });

  it('verifies all 4 curated studio presets exist and produce valid LUT tables', () => {
    const expectedPresets = [
      'Default (Pure Natural)',
      'Bright Meeting HD',
      'Warm Creator Look',
      'Monochrome Film',
    ];
    for (const name of expectedPresets) {
      assert.ok(FACTORY_PRESETS[name], `Missing preset: ${name}`);
      const merged = { ...DEFAULT_STUDIO_PARAMS, ...FACTORY_PRESETS[name] };
      const { rLUT, gLUT, bLUT } = buildColorGradingLUTs(merged);
      assert.equal(rLUT.length, 256);
      assert.equal(gLUT.length, 256);
      assert.equal(bLUT.length, 256);
    }
  });

  it('computes 64-bin RGB + Luminance histograms', () => {
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
