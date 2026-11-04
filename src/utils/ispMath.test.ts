import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_STUDIO_PARAMS,
  FACTORY_PRESETS,
  build256LUT,
  parseCubeLUTText,
  stepGimbalEMA,
  getFpsBadgeColor,
  formatMasterTimecode,
  computeHistogram64FromRGBA,
} from "./ispMath";

test("FPS telemetry badge color follows exact thresholds (>=27.5 emerald, 18-27.4 amber, <18 crimson)", () => {
  assert.equal(getFpsBadgeColor(30.0), "#10B981");
  assert.equal(getFpsBadgeColor(27.5), "#10B981");
  assert.equal(getFpsBadgeColor(24.0), "#F59E0B");
  assert.equal(getFpsBadgeColor(18.0), "#F59E0B");
  assert.equal(getFpsBadgeColor(15.0), "#E11D48");
});

test("Master timecode formats frames into HH:MM:SS:FF accurately at 30 FPS", () => {
  assert.equal(formatMasterTimecode(0, 30), "00:00:00:00");
  assert.equal(formatMasterTimecode(45, 30), "00:00:01:15");
  assert.equal(formatMasterTimecode(30 * 65 + 12, 30), "00:01:05:12");
});

test("256x3 LUT engine produces monotonic Rec.709 neutral curve and lifted Matte Obsidian floor", () => {
  const neutralParams = {
    ...DEFAULT_STUDIO_PARAMS,
    film_look: "Rec.709 Neutral" as const,
    scurve_contrast: 0,
    shadows_lift: 0,
    highlights_gain: 0,
    midtones_gamma: 1.0,
    temp_shift: 0,
    tint_shift: 0,
  };
  const lutNeutral = build256LUT(neutralParams);
  assert.equal(lutNeutral.r[0], 0);
  assert.equal(lutNeutral.r[255], 255);
  assert.ok(lutNeutral.r[128] >= 126 && lutNeutral.r[128] <= 130);

  const obsidianParams = {
    ...neutralParams,
    film_look: "Matte Obsidian" as const,
    lut_intensity: 100,
  };
  const lutObsidian = build256LUT(obsidianParams);
  // Matte Obsidian lifts black floor (x=0 -> ~0.06 * 255 = ~15)
  assert.ok(lutObsidian.r[0] >= 12);
});

test("Gimbal EMA smoothly interpolates zoom, panX, and panY within safe bounds", () => {
  const next = stepGimbalEMA(
    { zoom: 1.0, panX: 0.0, panY: 0.0 },
    { zoom: 2.0, panX: 0.5, panY: -0.5 },
    0.1
  );
  assert.ok(Math.abs(next.zoom - 1.1) < 1e-5);
  assert.ok(Math.abs(next.panX - 0.05) < 1e-5);
  assert.ok(Math.abs(next.panY - -0.05) < 1e-5);
});

test(".CUBE LUT parser handles 1D LUT data and rejects malformed input", () => {
  const sampleCube = `
TITLE "Test Studio LUT"
LUT_1D_SIZE 3
0.0 0.0 0.0
0.5 0.4 0.6
1.0 1.0 1.0
`;
  const parsed = parseCubeLUTText(sampleCube);
  assert.equal(parsed.valid, true);
  assert.equal(parsed.r[0], 0);
  assert.ok(Math.abs(parsed.g[127] - 0.4) < 0.05);
  assert.equal(parsed.b[255], 1);

  const bad = parseCubeLUTText("INVALID HEADER ONLY");
  assert.equal(bad.valid, false);
});

test("64-bin RGB and Luma histogram normalizes peaks into [0, 1]", () => {
  const rgba = new Uint8ClampedArray(16 * 16 * 4);
  for (let i = 0; i < rgba.length; i += 4) {
    rgba[i] = 200; // R
    rgba[i + 1] = 100; // G
    rgba[i + 2] = 50; // B
    rgba[i + 3] = 255;
  }
  const hist = computeHistogram64FromRGBA(rgba, 16, 16, 1);
  assert.equal(hist.r[200 >> 2], 1.0);
  assert.equal(hist.g[100 >> 2], 1.0);
  assert.equal(hist.b[50 >> 2], 1.0);
  assert.equal( Object.keys(FACTORY_PRESETS).length, 4);
});
