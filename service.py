"""Clip service: owns capture/audio/voice/buffers and exports clips with ffmpeg."""
import os
import subprocess
import tempfile
import threading
import time
import wave

import imageio_ffmpeg
import numpy as np
from PySide6.QtCore import QObject, Signal

from audio import OUT_RATE, AudioSource
from capture import FrameBuffer, ScreenCapture
from settings import THUMB_DIR, Settings
from voice import VoiceEngine

_DETECTED_ENCODER = None


def get_hardware_video_encoder():
    """Detects available hardware encoder (AMF, NVENC, QSV) with fallback to libx264."""
    global _DETECTED_ENCODER
    if _DETECTED_ENCODER is not None:
        return _DETECTED_ENCODER

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    candidates = ["h264_nvenc", "h264_amf", "h264_qsv"]
    for enc in candidates:
        test_cmd = [exe, "-f", "lavfi", "-i", "nullsrc=s=128x128:d=0.05", "-c:v", enc, "-f", "null", "-"]
        try:
            p = subprocess.run(test_cmd, capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                _DETECTED_ENCODER = enc
                return _DETECTED_ENCODER
        except Exception:  # noqa: BLE001
            pass

    _DETECTED_ENCODER = "libx264"
    return _DETECTED_ENCODER


def get_encoder_args(encoder_name: str, quality: str) -> list:
    if encoder_name == "h264_amf":
        qp = {"Low": ("28", "30"), "Medium": ("22", "24"), "High": ("18", "20")}.get(quality, ("22", "24"))
        return [
            "-c:v", "h264_amf",
            "-usage", "transcoding",
            "-rc", "cqp",
            "-qp_i", qp[0],
            "-qp_p", qp[1],
            "-quality", "speed" if quality != "High" else "quality",
        ]
    elif encoder_name == "h264_nvenc":
        cq = {"Low": "28", "Medium": "23", "High": "18"}.get(quality, "23")
        return ["-c:v", "h264_nvenc", "-cq", cq, "-preset", "p4"]
    elif encoder_name == "h264_qsv":
        gq = {"Low": "28", "Medium": "23", "High": "18"}.get(quality, "23")
        return ["-c:v", "h264_qsv", "-global_quality", gq, "-preset", "veryfast"]
    else:
        crf = {"Low": "28", "Medium": "23", "High": "18"}.get(quality, "23")
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf]


def thumb_path_for(clip_path: str) -> str:
    return os.path.join(THUMB_DIR, os.path.splitext(os.path.basename(clip_path))[0] + ".jpg")


class ClipService(QObject):
    clip_saved = Signal(str)
    clip_failed = Signal(str)
    voice_triggered = Signal(str, int)  # phrase, duration

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.buffer = FrameBuffer()
        self.capture = ScreenCapture(self.buffer)
        self.system = AudioSource("system")
        self.mic = AudioSource("mic")
        self.voice = VoiceEngine()

        self._saving = threading.Lock()
        self.saving = False
        self._applied = None

        # Connect mic stream to voice engine
        self.mic.pcm_listener = self.voice.feed_pcm
        self.voice.triggered.connect(self._on_voice_triggered)

    def _on_voice_triggered(self, phrase: str, duration: int):
        self.voice_triggered.emit(phrase, duration)
        self.save_clip(duration=duration, reason=f"voice: {phrase}")

    # ---- lifecycle -------------------------------------------------
    def apply(self, s: Settings):
        old = self._applied
        self.settings = s

        # Adjust buffer capacity to max needed duration
        max_duration = s.max_buffer_duration()
        self.buffer.max_seconds = max_duration
        self.system.max_seconds = self.mic.max_seconds = max_duration

        if old is None or old.video_restart_key() != s.video_restart_key() or not self.capture.running():
            self.buffer.clear()
            self.capture.start(s.monitor, s.fps, s.resolution)

        if old is None or old.system_audio != s.system_audio:
            self.system.start() if s.system_audio else self.system.stop()
            self.system.clear()

        # Microphone is needed if mic_audio is enabled OR voice_clipping is enabled
        need_mic = s.mic_audio or s.voice_clipping_enabled
        old_need_mic = (old.mic_audio or old.voice_clipping_enabled) if old else False
        if old is None or old_need_mic != need_mic:
            self.mic.start() if need_mic else self.mic.stop()
            self.mic.clear()

        # Update voice engine
        self.voice.update_config(s.voice_clipping_enabled, s.voice_triggers)
        if s.voice_clipping_enabled:
            self.voice.start()
        else:
            self.voice.stop()

        self._applied = Settings(**s.__dict__)

    def shutdown(self):
        self.capture.stop()
        self.system.stop()
        self.mic.stop()
        self.voice.stop()

    @property
    def paused(self):
        return self.capture.paused

    def set_paused(self, value: bool):
        if self.capture.paused and not value:
            self.buffer.clear()
            self.system.clear()
            self.mic.clear()
        self.capture.paused = value

    # ---- export ----------------------------------------------------
    def save_clip(self, duration: int = None, reason: str = "hotkey"):
        if self.saving:
            return
        frames = self.buffer.snapshot()
        if len(frames) < 2:
            self.clip_failed.emit("Nothing buffered yet. Wait a moment and try again.")
            return

        target_duration = int(duration) if duration is not None else self.settings.clip_length
        cutoff = frames[-1][0] - target_duration
        clip_frames = [f for f in frames if f[0] >= cutoff]
        if len(clip_frames) < 2:
            clip_frames = frames

        self.saving = True
        threading.Thread(
            target=self._export,
            args=(clip_frames, Settings(**self.settings.__dict__)),
            daemon=True
        ).start()

    def _export(self, frames, s: Settings):
        wav_path = None
        try:
            os.makedirs(s.save_dir, exist_ok=True)
            os.makedirs(THUMB_DIR, exist_ok=True)
            base = time.strftime(s.filename_template) or "Clip"
            base = "".join(c for c in base if c not in '<>:"/\\|?*')
            out = os.path.join(s.save_dir, base + ".mp4")
            n = 1
            while os.path.exists(out):
                out = os.path.join(s.save_dir, f"{base}_{n}.mp4")
                n += 1

            t0, t1 = frames[0][0], frames[-1][0]
            fps = max(1.0, (len(frames) - 1) / max(t1 - t0, 0.001))

            # Save middle frame as thumbnail
            with open(thumb_path_for(out), "wb") as f:
                f.write(frames[len(frames) // 2][1])

            # Audio mix (only include mic if s.mic_audio is checked)
            mix = None
            for src, enabled, vol in (
                (self.system, s.system_audio, s.system_volume),
                (self.mic, s.mic_audio, s.mic_volume),
            ):
                if enabled and not src.error:
                    track = src.render(t0, t1, vol / 100.0)
                    mix = track if mix is None else mix + track

            cmd = [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-y",
                "-loglevel", "error",
                "-f", "image2pipe",
                "-framerate", f"{fps:.3f}",
                "-c:v", "mjpeg",
                "-i", "-",
            ]
            if mix is not None:
                pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
                fd, wav_path = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                with wave.open(wav_path, "wb") as w:
                    w.setnchannels(2)
                    w.setsampwidth(2)
                    w.setframerate(OUT_RATE)
                    w.writeframes(pcm.tobytes())
                cmd += ["-i", wav_path]

            # Video encoder (hardware accelerated or libx264)
            best_encoder = get_hardware_video_encoder()
            cmd += get_encoder_args(best_encoder, s.quality)
            cmd += ["-pix_fmt", "yuv420p"]

            if mix is not None:
                cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]
            cmd += ["-movflags", "+faststart", out]

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )

            def feed():
                try:
                    for _, data in frames:
                        proc.stdin.write(data)
                    proc.stdin.close()
                except OSError:
                    pass

            threading.Thread(target=feed, daemon=True).start()
            err = proc.stderr.read().decode(errors="replace")
            proc.wait()
            if proc.returncode != 0 or not os.path.exists(out):
                raise RuntimeError(err.strip() or "ffmpeg failed")
            self.clip_saved.emit(out)
        except Exception as e:  # noqa: BLE001
            self.clip_failed.emit(f"Could not save clip: {e}")
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
            self.saving = False
