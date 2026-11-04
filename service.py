"""Clip service: owns capture/audio/buffers and exports clips with ffmpeg."""
import os
import subprocess
import tempfile
import threading
import time
import wave

import numpy as np
import imageio_ffmpeg
from PySide6.QtCore import QObject, Signal

from audio import AudioSource, OUT_RATE
from capture import FrameBuffer, ScreenCapture
from settings import QUALITY_CRF, THUMB_DIR, Settings


def thumb_path_for(clip_path: str) -> str:
    return os.path.join(THUMB_DIR, os.path.splitext(os.path.basename(clip_path))[0] + ".jpg")


class ClipService(QObject):
    clip_saved = Signal(str)
    clip_failed = Signal(str)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.buffer = FrameBuffer()
        self.capture = ScreenCapture(self.buffer)
        self.system = AudioSource("system")
        self.mic = AudioSource("mic")
        self._saving = threading.Lock()
        self.saving = False
        self._applied = None

    # ---- lifecycle -------------------------------------------------
    def apply(self, s: Settings):
        old = self._applied
        self.settings = s
        self.buffer.max_seconds = s.clip_length
        self.system.max_seconds = self.mic.max_seconds = s.clip_length
        if old is None or old.video_restart_key() != s.video_restart_key() or not self.capture.running():
            self.buffer.clear()
            self.capture.start(s.monitor, s.fps, s.resolution)
        if old is None or old.system_audio != s.system_audio:
            self.system.start() if s.system_audio else self.system.stop()
            self.system.clear()
        if old is None or old.mic_audio != s.mic_audio:
            self.mic.start() if s.mic_audio else self.mic.stop()
            self.mic.clear()
        self._applied = Settings(**s.__dict__)

    def shutdown(self):
        self.capture.stop()
        self.system.stop()
        self.mic.stop()

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
    def save_clip(self):
        if self.saving:
            return
        frames = self.buffer.snapshot()
        if len(frames) < 2:
            self.clip_failed.emit("Nothing buffered yet. Wait a moment and try again.")
            return
        cutoff = frames[-1][0] - self.settings.clip_length
        frames = [f for f in frames if f[0] >= cutoff]
        self.saving = True
        threading.Thread(target=self._export, args=(frames, Settings(**self.settings.__dict__)),
                         daemon=True).start()

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
            with open(thumb_path_for(out), "wb") as f:
                f.write(frames[len(frames) // 2][1])

            mix = None
            for src, enabled, vol in ((self.system, s.system_audio, s.system_volume),
                                      (self.mic, s.mic_audio, s.mic_volume)):
                if enabled and not src.error:
                    track = src.render(t0, t1, vol / 100.0)
                    mix = track if mix is None else mix + track
            cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                   "-f", "image2pipe", "-framerate", f"{fps:.3f}", "-c:v", "mjpeg", "-i", "-"]
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
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(QUALITY_CRF[s.quality]),
                    "-pix_fmt", "yuv420p"]
            if mix is not None:
                cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]
            cmd += ["-movflags", "+faststart", out]

            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                    creationflags=0x08000000)  # CREATE_NO_WINDOW

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
                os.remove(wav_path)
            self.saving = False

