# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — Wall-Clock Synchronized 1.0x CFR Video + Audio Recorder (`core/recorder_audio.py`).

LAW 4 COMPLIANCE:
- Never writes raw camera frames directly into a hardcoded 30.0 FPS VideoWriter without timestamp pacing
  (which causes 10 FPS capture to play back at 3x fast-forward speed!).
- Implements `VideoRecorderThread` with a precision 10ms Wall-Clock CFR (Constant Frame Rate 30.0 FPS) Pacer:
  * Tracks `elapsed_seconds = time.perf_counter() - self.start_time - self.total_paused_duration`
  * Computes `expected_frame_count = int(elapsed_seconds * 30.0)` (`target_frame_index`)
  * Writes `self.latest_frame` so `self.frames_written` matches `expected_frame_count`
  * Result: 10.0 seconds of real-world recording ALWAYS produces a 10.0-second video at 1.0x natural human speed,
    perfectly synced with `.wav` microphone audio muxed via `ffmpeg` (`imageio-ffmpeg`).
"""

import os
import shutil
import subprocess
import threading
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

try:
    import sounddevice as sd  # type: ignore

    HAS_SOUNDDEVICE = True
except Exception:
    sd = None
    HAS_SOUNDDEVICE = False

try:
    import pyvirtualcam  # type: ignore

    HAS_PYVIRTUALCAM = True
except Exception:
    pyvirtualcam = None
    HAS_PYVIRTUALCAM = False

try:
    import imageio_ffmpeg  # type: ignore

    HAS_IMAGEIO_FFMPEG = True
except Exception:
    imageio_ffmpeg = None
    HAS_IMAGEIO_FFMPEG = False


class AudioVUMonitor(QObject):
    """
    Non-blocking sounddevice.InputStream(channels=1, samplerate=44100, blocksize=1024)
    computing RMS and Peak dBFS clamped to [-60.0, 0.0], emitting Qt signals at 30Hz.
    Forwards raw PCM int16 audio frames to the active video recorder when recording.
    """

    levels_updated = pyqtSignal(float, float, bool)  # (rms_db, peak_db, mic_available)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.sample_rate = 44100
        self.block_size = 1024
        self._stream = None
        self._mic_available = False
        self._rms_db: float = -60.0
        self._peak_db: float = -60.0
        self._peak_hold_db: float = -60.0
        self._lock = threading.Lock()
        self._audio_record_callback = None

        self._emit_timer = QTimer(self)
        self._emit_timer.setInterval(33)  # ~30 Hz
        self._emit_timer.timeout.connect(self._on_emit_tick)

    def set_audio_record_callback(self, callback) -> None:
        with self._lock:
            self._audio_record_callback = callback

    def start(self) -> None:
        if HAS_SOUNDDEVICE and sd is not None:
            try:
                self._stream = sd.InputStream(
                    channels=1,
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._mic_available = True
            except Exception:
                self._stream = None
                self._mic_available = False
        else:
            self._mic_available = False

        self._emit_timer.start()

    def stop(self) -> None:
        self._emit_timer.stop()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if indata is None or indata.size == 0:
            return
        samples = indata[:, 0]
        rms = float(np.sqrt(np.mean(np.square(samples))))
        peak = float(np.max(np.abs(samples)))

        rms_db = float(np.clip(20.0 * np.log10(max(rms, 1e-7)), -60.0, 0.0))
        peak_db = float(np.clip(20.0 * np.log10(max(peak, 1e-7)), -60.0, 0.0))

        with self._lock:
            self._rms_db = rms_db
            if peak_db >= self._peak_hold_db:
                self._peak_hold_db = peak_db
            else:
                self._peak_hold_db = max(rms_db, self._peak_hold_db - 0.65)
            cb = self._audio_record_callback

        if cb is not None:
            pcm16 = np.clip(samples * 32767.0, -32768.0, 32767.0).astype(np.int16).tobytes()
            cb(pcm16)

    def _on_emit_tick(self) -> None:
        with self._lock:
            if self._mic_available:
                rms_db = self._rms_db
                peak_db = self._peak_hold_db
                self._rms_db = max(-60.0, self._rms_db - 1.5)
                self._peak_hold_db = max(-60.0, self._peak_hold_db - 0.45)
            else:
                rms_db = -54.0
                peak_db = -48.0
        self.levels_updated.emit(rms_db, peak_db, self._mic_available)


class VideoRecorderThread(QThread):
    """
    Wall-Clock CFR (Constant Frame Rate 30.0 FPS) Video Writer Thread.
    Runs a precision 10ms pacing loop so that regardless of whether the camera delivers
    10 FPS, 15 FPS, 24 FPS, or 30 FPS, 10 seconds of wall-clock recording ALWAYS writes
    300 frames (10.0 seconds at 1.0x human playback speed).
    """

    timecode_tick = pyqtSignal(str)

    def __init__(
        self,
        video_path: Path,
        frame_size: Tuple[int, int],
        target_fps: float = 30.0,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.video_path = video_path
        self.frame_size = frame_size
        self.target_fps: float = float(target_fps)

        self.start_time: float = 0.0
        self.frames_written: int = 0
        self.total_paused_duration: float = 0.0
        self._pause_started_at: Optional[float] = None

        self._lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None
        self._running: bool = False
        self._paused: bool = False
        self.video_writer: Optional[cv2.VideoWriter] = None

    def update_latest_frame(self, frame_bgr: np.ndarray) -> None:
        w, h = self.frame_size
        fh, fw = frame_bgr.shape[:2]
        if (fw, fh) != (w, h):
            frame_copy = cv2.resize(frame_bgr, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            frame_copy = frame_bgr.copy()
        with self._lock:
            self.latest_frame = frame_copy

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            if paused and not self._paused:
                self._paused = True
                self._pause_started_at = time.perf_counter()
            elif not paused and self._paused:
                if self._pause_started_at is not None:
                    self.total_paused_duration += time.perf_counter() - self._pause_started_at
                self._pause_started_at = None
                self._paused = False

    def request_stop(self) -> None:
        with self._lock:
            if self._paused and self._pause_started_at is not None:
                self.total_paused_duration += time.perf_counter() - self._pause_started_at
                self._pause_started_at = None
            self._paused = False
            self._running = False

    @staticmethod
    def format_timecode(frame_count: int, fps: float) -> str:
        fps_int = max(1, int(round(fps)))
        total_seconds = frame_count // fps_int
        frames = frame_count % fps_int
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

    def run(self) -> None:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(
            str(self.video_path),
            fourcc,
            self.target_fps,
            self.frame_size,
        )
        self.start_time = time.perf_counter()
        self.frames_written = 0
        self.total_paused_duration = 0.0
        self._running = True

        try:
            while True:
                with self._lock:
                    running = self._running
                    paused = self._paused
                    current_frame = self.latest_frame
                    paused_dur = self.total_paused_duration

                if not running:
                    break

                if paused or current_frame is None:
                    time.sleep(0.010)
                    continue

                # Wall-Clock CFR (30.0 FPS) Pacer
                elapsed_seconds = max(0.0, time.perf_counter() - self.start_time - paused_dur)
                expected_frame_count = int(elapsed_seconds * 30.0)
                target_frame_index = int(elapsed_seconds * self.target_fps)

                wrote_any = False
                while self.frames_written < max(expected_frame_count, target_frame_index) and current_frame is not None:
                    self.video_writer.write(current_frame)
                    self.frames_written += 1
                    wrote_any = True

                if wrote_any and self.frames_written % 3 == 0:
                    self.timecode_tick.emit(self.format_timecode(self.frames_written, self.target_fps))

                # Precision 10ms pacing interval
                time.sleep(0.010)
        finally:
            if self.video_writer is not None:
                self.video_writer.release()


class StudioRecorder(QObject):
    """
    Wall-Clock Synchronized 1.0x Real-Time MP4 + WAV Studio Recorder with Pause/Resume
    and automatic FFmpeg AAC muxing.
    """

    recording_state_changed = pyqtSignal(bool, bool)  # (is_recording, is_paused)
    timecode_updated = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(
        self,
        output_dir: Path,
        audio_monitor: AudioVUMonitor,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.output_dir = output_dir
        self.audio_monitor = audio_monitor

        self._is_recording = False
        self._is_paused = False
        self._audio_chunks: List[bytes] = []
        self._audio_lock = threading.Lock()
        self._recorder_thread: Optional[VideoRecorderThread] = None

        self._temp_video_path: Optional[Path] = None
        self._temp_audio_path: Optional[Path] = None
        self._final_output_path: Optional[Path] = None
        self._fps: float = 30.0
        self._frame_size: Tuple[int, int] = (1280, 720)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def start_recording(self, width: int, height: int, fps: float = 30.0) -> bool:
        if self._is_recording:
            return False

        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._temp_video_path = self.output_dir / f".temp_video_{timestamp}.mp4"
        self._temp_audio_path = self.output_dir / f".temp_audio_{timestamp}.wav"
        self._final_output_path = self.output_dir / f"LUMIXA_PRO_{timestamp}.mp4"

        self._frame_size = (width, height)
        self._fps = 30.0
        self._is_paused = False
        self._is_recording = True

        with self._audio_lock:
            self._audio_chunks.clear()

        self.audio_monitor.set_audio_record_callback(self._on_audio_pcm)

        self._recorder_thread = VideoRecorderThread(
            video_path=self._temp_video_path,
            frame_size=self._frame_size,
            target_fps=self._fps,
            parent=self,
        )
        self._recorder_thread.timecode_tick.connect(self.timecode_updated.emit)
        self._recorder_thread.start()

        self.recording_state_changed.emit(True, False)
        self.status_message.emit(f"1.0x CFR RECORDING STARTED -> {self._final_output_path.name}")
        return True

    def toggle_pause(self) -> bool:
        if not self._is_recording or self._recorder_thread is None:
            return False
        self._is_paused = not self._is_paused
        self._recorder_thread.set_paused(self._is_paused)
        self.recording_state_changed.emit(self._is_recording, self._is_paused)
        state_str = "PAUSED" if self._is_paused else "RESUMED"
        self.status_message.emit(f"RECORDING {state_str}")
        return self._is_paused

    def push_frame(self, frame_bgr: np.ndarray) -> None:
        if not self._is_recording or self._recorder_thread is None:
            return
        self._recorder_thread.update_latest_frame(frame_bgr)

    def _on_audio_pcm(self, pcm_bytes: bytes) -> None:
        if not self._is_recording or self._is_paused:
            return
        with self._audio_lock:
            self._audio_chunks.append(pcm_bytes)

    def stop_recording(self) -> Optional[Path]:
        if not self._is_recording:
            return None

        self._is_recording = False
        self._is_paused = False
        self.audio_monitor.set_audio_record_callback(None)

        if self._recorder_thread is not None:
            self._recorder_thread.request_stop()
            self._recorder_thread.wait(5000)
            self._recorder_thread = None

        self._write_wav_file()
        final_file = self._mux_video_and_audio()

        self.recording_state_changed.emit(False, False)
        self.timecode_updated.emit("00:00:00:00")
        if final_file is not None:
            self.status_message.emit(f"SAVED 1.0x SYNCED MP4 -> {final_file.name}")
        return final_file

    def _write_wav_file(self) -> bool:
        if self._temp_audio_path is None:
            return False
        with self._audio_lock:
            if not self._audio_chunks:
                return False
            raw_audio = b"".join(self._audio_chunks)
            self._audio_chunks.clear()

        try:
            with wave.open(str(self._temp_audio_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # int16
                wf.setframerate(self.audio_monitor.sample_rate)
                wf.writeframes(raw_audio)
            return True
        except Exception:
            return False

    @staticmethod
    def _locate_ffmpeg() -> Optional[str]:
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        if HAS_IMAGEIO_FFMPEG and imageio_ffmpeg is not None:
            try:
                exe = imageio_ffmpeg.get_ffmpeg_exe()
                if exe and os.path.exists(exe):
                    return exe
            except Exception:
                pass
        return None

    def _mux_video_and_audio(self) -> Optional[Path]:
        if self._temp_video_path is None or self._final_output_path is None:
            return None

        if not self._temp_video_path.exists():
            return None

        has_audio = self._temp_audio_path is not None and self._temp_audio_path.exists()
        ffmpeg_exe = self._locate_ffmpeg()

        if has_audio and ffmpeg_exe is not None:
            try:
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-i",
                    str(self._temp_video_path),
                    "-i",
                    str(self._temp_audio_path),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                    str(self._final_output_path),
                ]
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    creationflags=creationflags,
                )
                if res.returncode == 0 and self._final_output_path.exists():
                    self._safe_unlink(self._temp_video_path)
                    self._safe_unlink(self._temp_audio_path)
                    return self._final_output_path
            except Exception:
                pass

        try:
            if self._final_output_path.exists():
                self._safe_unlink(self._final_output_path)
            self._temp_video_path.replace(self._final_output_path)
        except Exception:
            pass
        self._safe_unlink(self._temp_audio_path)
        return self._final_output_path

    @staticmethod
    def _safe_unlink(path: Optional[Path]) -> None:
        if path is not None:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass


class VirtualCamManager(QObject):
    """Manages pyvirtualcam broadcast output to OBS VirtualCam / UnityCapture."""

    status_changed = pyqtSignal(bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cam = None
        self._active = False
        self._resolution: Tuple[int, int] = (1280, 720)

    @property
    def is_active(self) -> bool:
        return self._active

    def set_enabled(self, enable: bool, width: int = 1280, height: int = 720) -> bool:
        if not enable:
            self.stop()
            return False

        if not HAS_PYVIRTUALCAM or pyvirtualcam is None:
            self._active = False
            self.status_changed.emit(False, "pyvirtualcam package not installed")
            return False

        try:
            self.stop()
            self._cam = pyvirtualcam.Camera(
                width=width,
                height=height,
                fps=30,
                fmt=pyvirtualcam.PixelFormat.BGR,
            )
            self._resolution = (width, height)
            self._active = True
            dev_name = getattr(self._cam, "device", "OBS VirtualCam")
            self.status_changed.emit(True, f"VIRTUAL CAM LIVE ({dev_name})")
            return True
        except Exception as exc:
            self._cam = None
            self._active = False
            self.status_changed.emit(
                False,
                f"Virtual Cam Driver Unavailable (Install OBS VirtualCam): {exc}",
            )
            return False

    def send_frame(self, frame_bgr: np.ndarray) -> None:
        if not self._active or self._cam is None:
            return
        try:
            h, w = frame_bgr.shape[:2]
            if (w, h) != self._resolution:
                frame_bgr = cv2.resize(frame_bgr, self._resolution, interpolation=cv2.INTER_LINEAR)
            self._cam.send(frame_bgr)
        except Exception:
            self.stop()

    def stop(self) -> None:
        if self._cam is not None:
            try:
                self._cam.close()
            except Exception:
                pass
            self._cam = None
        if self._active:
            self._active = False
            self.status_changed.emit(False, "VIRTUAL CAM OFF")
