"""Screen capture into a time-bounded ring buffer of JPEG frames."""
import threading
import time
from collections import deque

import cv2
import mss
import numpy as np

from settings import RESOLUTIONS


class FrameBuffer:
    def __init__(self):
        self._frames = deque()  # (monotonic_ts, jpeg_bytes)
        self._lock = threading.Lock()
        self.max_seconds = 30

    def add(self, ts, data):
        with self._lock:
            self._frames.append((ts, data))
            cutoff = ts - self.max_seconds
            while self._frames and self._frames[0][0] < cutoff:
                self._frames.popleft()

    def snapshot(self):
        with self._lock:
            return list(self._frames)

    def clear(self):
        with self._lock:
            self._frames.clear()

    def span(self) -> float:
        with self._lock:
            if len(self._frames) < 2:
                return 0.0
            return self._frames[-1][0] - self._frames[0][0]

    def size_bytes(self) -> int:
        with self._lock:
            return sum(len(d) for _, d in self._frames)


def target_size(src_w, src_h, res_name):
    target_h = RESOLUTIONS.get(res_name, 0)
    if target_h == 0 or target_h >= src_h:
        w, h = src_w, src_h
    else:
        h = target_h
        w = int(round(src_w * target_h / src_h))
    return w - (w % 2), h - (h % 2)


class ScreenCapture:
    def __init__(self, buffer: FrameBuffer):
        self.buffer = buffer
        self._thread = None
        self._stop = threading.Event()
        self.paused = False
        self.error = None
        self.frame_size = (0, 0)
        self.actual_fps = 0.0

    def start(self, monitor_index: int, fps: int, resolution: str):
        self.stop()
        self._stop.clear()
        self.error = None
        self._thread = threading.Thread(
            target=self._run, args=(monitor_index, fps, resolution), daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread:
            self._stop.set()
            self._thread.join(timeout=3)
        self._thread = None

    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self, monitor_index, fps, resolution):
        try:
            with mss.mss() as sct:
                mons = sct.monitors
                mon = mons[monitor_index] if 0 < monitor_index < len(mons) else mons[1]
                interval = 1.0 / fps
                nxt = time.monotonic()
                count, t0 = 0, time.monotonic()
                while not self._stop.is_set():
                    now = time.monotonic()
                    if now < nxt:
                        time.sleep(min(nxt - now, 0.005))
                        continue
                    nxt += interval
                    if nxt < now - interval * 2:  # fell behind, resync
                        nxt = now + interval
                    if self.paused:
                        continue
                    img = np.asarray(sct.grab(mon))[:, :, :3]  # BGRA -> BGR
                    w, h = target_size(img.shape[1], img.shape[0], resolution)
                    if (w, h) != (img.shape[1], img.shape[0]):
                        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
                    self.frame_size = (w, h)
                    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ok:
                        self.buffer.add(time.monotonic(), enc.tobytes())
                    count += 1
                    if time.monotonic() - t0 >= 2:
                        self.actual_fps = count / (time.monotonic() - t0)
                        count, t0 = 0, time.monotonic()
        except Exception as e:  # noqa: BLE001
            self.error = str(e)

