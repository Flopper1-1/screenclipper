"""System-audio (WASAPI loopback) and microphone capture into PCM ring buffers."""
import threading
import time
from collections import deque

import numpy as np

try:
    import pyaudiowpatch as pyaudio
except Exception:  # noqa: BLE001
    pyaudio = None

OUT_RATE = 48000


class AudioSource:
    """One input stream. Stores (end_ts, samples[float32, n x 2], rate)."""

    def __init__(self, kind: str):
        self.kind = kind  # "system" | "mic"
        self.chunks = deque()
        self.max_seconds = 30
        self._lock = threading.Lock()
        self._pa = None
        self._stream = None
        self.channels = 2
        self.rate = OUT_RATE
        self.error = None

    def start(self):
        self.stop()
        if pyaudio is None:
            self.error = "Audio library unavailable"
            return
        try:
            self._pa = pyaudio.PyAudio()
            if self.kind == "system":
                dev = self._pa.get_default_wasapi_loopback()
            else:
                dev = self._pa.get_default_input_device_info()
            self.channels = max(1, int(dev["maxInputChannels"]))
            self.rate = int(dev["defaultSampleRate"])
            self._stream = self._pa.open(
                format=pyaudio.paInt16, channels=self.channels, rate=self.rate,
                input=True, input_device_index=dev["index"],
                frames_per_buffer=1024, stream_callback=self._callback)
            self.error = None
        except Exception as e:  # noqa: BLE001
            self.error = str(e)
            self.stop()

    def stop(self):
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
            if self._pa:
                self._pa.terminate()
        except Exception:  # noqa: BLE001
            pass
        self._stream = self._pa = None

    def clear(self):
        with self._lock:
            self.chunks.clear()

    def _callback(self, in_data, frame_count, time_info, status):
        ts = time.monotonic()
        data = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
        data = data.reshape(-1, self.channels)
        if self.channels == 1:
            data = np.repeat(data, 2, axis=1)
        else:
            data = data[:, :2]
        with self._lock:
            self.chunks.append((ts, data, self.rate))
            while self.chunks and self.chunks[0][0] < ts - self.max_seconds - 2:
                self.chunks.popleft()
        return (None, pyaudio.paContinue)

    def render(self, t0: float, t1: float, volume: float) -> np.ndarray:
        """Place chunks on a continuous OUT_RATE timeline (silence fills gaps;
        WASAPI loopback delivers nothing while the desktop is silent)."""
        n = max(1, int((t1 - t0) * OUT_RATE))
        out = np.zeros((n, 2), dtype=np.float32)
        with self._lock:
            chunks = list(self.chunks)
        for end_ts, data, rate in chunks:
            if rate != OUT_RATE:
                m = int(len(data) * OUT_RATE / rate)
                if m < 1:
                    continue
                x_old = np.linspace(0, 1, len(data), endpoint=False)
                x_new = np.linspace(0, 1, m, endpoint=False)
                data = np.stack([np.interp(x_new, x_old, data[:, c]) for c in range(2)], axis=1)
            dur = len(data) / OUT_RATE
            start = int((end_ts - dur - t0) * OUT_RATE)
            a, b = max(start, 0), min(start + len(data), n)
            if b <= a:
                continue
            out[a:b] += data[a - start:b - start] * volume
        return out

