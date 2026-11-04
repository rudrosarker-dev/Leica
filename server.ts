import express from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, ThinkingLevel } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PYTHON_REPO_FILES = [
  "README.md",
  "main.py",
  "requirements.txt",
  "setup_and_run.bat",
  "build_exe.bat",
  "core/__init__.py",
  "core/camera_engine.py",
  "core/color_lut.py",
  "core/ai_processor.py",
  "core/recorder_audio.py",
  "core/preset_manager.py",
  "ui/__init__.py",
  "ui/styles.py",
  "ui/widgets.py",
  "ui/viewport_hud.py",
  "ui/main_window.py",
];

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: "4mb" }));

  // Endpoint to read the generated Python Desktop Repository files directly from disk
  app.get("/api/repo-files", (_req, res) => {
    try {
      const files = PYTHON_REPO_FILES.map((relPath) => {
        const fullPath = path.resolve(__dirname, relPath);
        let content = "";
        let sizeBytes = 0;
        let exists = false;
        if (fs.existsSync(fullPath)) {
          content = fs.readFileSync(fullPath, "utf-8");
          sizeBytes = Buffer.byteLength(content, "utf-8");
          exists = true;
        }
        const lines = content ? content.split(/\r?\n/).length : 0;
        return {
          path: relPath,
          exists,
          lines,
          sizeBytes,
          content,
        };
      });
      res.json({
        status: "ok",
        totalFiles: files.length,
        allPresent: files.every((f) => f.exists && f.lines > 0),
        files,
      });
    } catch (error) {
      res.status(500).json({
        status: "error",
        message: error instanceof Error ? error.message : "Failed to read repository files",
      });
    }
  });

  // High-Thinking Optical ISP & DirectShow Calibration Advisor endpoint using gemini-4-argon
  app.post("/api/isp-diag", async (req, res) => {
    const { params, telemetry, query } = req.body ?? {};
    const apiKey = process.env.GEMINI_API_KEY;

    const fallbackReport = [
      `OPTICAL ISP & UVC TIMING ANALYSIS — LOGITECH C270 HD`,
      `1. DirectShow Register Lock: CAP_PROP_AUTO_EXPOSURE = ${params?.manual_exposure_lock ? "0.25 (MANUAL LOCKED)" : "0.75 (AUTO)"} | Shutter = ${params?.hardware_exposure ?? -5} EV | Analog/Digital Gain = ${params?.hardware_gain ?? 110} ISO.`,
      `2. Frame Pacing & Flicker: ${params?.anti_flicker_50hz ? "50Hz Powerline Anti-Flicker active" : "60Hz Powerline mode"} — locks sensor integration window to prevent indoor fluorescent/LED banding while maintaining ${telemetry?.fps ? Number(telemetry.fps).toFixed(1) : "30.0"} FPS.`,
      `3. Colorimetry Pipeline: Active transfer curve [${params?.film_look ?? "Kodak Portra 400"}] @ ${params?.lut_intensity ?? 100}% mix | Gamma ${Number(params?.midtones_gamma ?? 1.0).toFixed(2)} | S-Curve ${Number(params?.scurve_contrast ?? 0.15).toFixed(2)} | Smart HSV Vibrance ${params?.vibrance ?? 15}.`,
      `4. Spatial Acutance & AI Segmentation: Mode [${params?.ai_mode ?? "Studio Spotlight"}] | Unsharp Mask Clarity ${Number(params?.optical_clarity ?? 0.8).toFixed(2)} | YCrCb Chroma/Luma Denoise ${Number(params?.denoise_strength ?? 0.15).toFixed(2)} | Output ${params?.upscale_1080p ? "1920x1080 Lanczos4 Master" : "1280x720 Native"}.`,
    ].join("\n");

    if (!apiKey || apiKey === "MY_GEMINI_API_KEY") {
      res.json({
        model: "gemini-4-argon (Deterministic Optical ISP Fallback)",
        thinkingLevel: "HIGH",
        analysis: fallbackReport,
      });
      return;
    }

    try {
      const ai = new GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build",
          },
        },
      });

      const promptText = `You are a Principal Optical ISP & UVC Hardware Engineer from Leica Camera AG and Blackmagic Design.
Analyze the following live Logitech C270 HD Studio pipeline parameters and user query, and provide a concise, mathematically rigorous 4-point calibration recommendation covering DirectShow exposure/gain trade-offs, SNR chroma denoising, 1D/3D LUT tonemapping, and portrait lighting separation. Keep your response under 160 words in plain technical prose without emojis.

Current Parameters: ${JSON.stringify(params ?? {})}
Live Telemetry: ${JSON.stringify(telemetry ?? {})}
Engineer Query: ${query || "Optimize current C270 low-light 30FPS studio calibration and color science."}`;

      const response = await ai.models.generateContent({
        model: "gemini-4-argon",
        contents: promptText,
        config: {
          systemInstruction:
            "Provide concise, mathematically rigorous optical ISP and UVC hardware engineering calibration advice in plain technical text without emojis. Keep output under 160 words.",
          thinkingConfig: {
            thinkingLevel: ThinkingLevel.HIGH,
          },
        },
      });

      res.json({
        model: "gemini-4-argon",
        thinkingLevel: "HIGH",
        analysis: response.text || fallbackReport,
      });
    } catch (_err) {
      res.json({
        model: "gemini-4-argon (Deterministic Optical ISP Fallback)",
        thinkingLevel: "HIGH",
        analysis: fallbackReport,
      });
    }
  });

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, "dist");
    app.use(express.static(distPath));
    app.get("*all", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`LEICA // C270 OPTIX STUDIO Server listening on http://localhost:${PORT}`);
  });
}

startServer();
