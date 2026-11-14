"""High-performance screen capture into a time-bounded ring buffer."""
import queue
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
        self._total_bytes = 0

    def add(self, ts, data):
        with self._lock:
            self._frames.append((ts, data))
            self._total_bytes += len(data)
            cutoff = ts - self.max_seconds
            while self._frames and self._frames[0][0] < cutoff:
                old_ts, old_data = self._frames.popleft()
                self._total_bytes -= len(old_data)

    def snapshot(self):
        with self._lock:
            return list(self._frames)

    def clear(self):
        with self._lock:
            self._frames.clear()
            self._total_bytes = 0

    def span(self) -> float:
        with self._lock:
            if len(self._frames) < 2:
                return 0.0
            return self._frames[-1][0] - self._frames[0][0]

    def size_bytes(self) -> int:
        with self._lock:
            return self._total_bytes


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
        self._workers = []
        self._raw_queue = queue.Queue(maxsize=3)
        self._stop = threading.Event()
        self.paused = False
        self.error = None
        self.frame_size = (0, 0)
        self.actual_fps = 0.0

    def start(self, monitor_index: int, fps: int, resolution: str):
        self.stop()
        self._stop.clear()
        self.error = None

        # Start compression worker
        self._workers = [
            threading.Thread(target=self._compression_worker, args=(resolution,), daemon=True)
            for _ in range(2)
        ]
        for w in self._workers:
            w.start()

        # Start capture thread
        self._thread = threading.Thread(
            target=self._run_capture, args=(monitor_index, fps), daemon=True
        )
        self._thread.start()

    def stop(self):
        if self._thread or self._workers:
            self._stop.set()
            if self._thread:
                self._thread.join(timeout=2)
            for w in self._workers:
                w.join(timeout=1)
            # Drain queue
            while not self._raw_queue.empty():
                try:
                    self._raw_queue.get_nowait()
                except queue.Empty:
                    break
        self._thread = None
        self._workers.clear()

    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def _compression_worker(self, resolution: str):
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
        while not self._stop.is_set():
            try:
                item = self._raw_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            ts, raw_img = item
            try:
                src_h, src_w = raw_img.shape[:2]
                w, h = target_size(src_w, src_h, resolution)
                if (w, h) != (src_w, src_h):
                    img = cv2.resize(raw_img, (w, h), interpolation=cv2.INTER_LINEAR)
                else:
                    img = raw_img

                self.frame_size = (w, h)
                ok, enc = cv2.imencode(".jpg", img, encode_params)
                if ok:
                    self.buffer.add(ts, enc.tobytes())
            except Exception:  # noqa: BLE001
                pass

    def _run_capture(self, monitor_index: int, fps: int):
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
                        time.sleep(min(nxt - now, 0.002))
                        continue
                    nxt += interval
                    if nxt < now - interval * 2:
                        nxt = now + interval

                    if self.paused:
                        continue

                    # Grab screenshot BGRA -> BGR
                    grabbed = sct.grab(mon)
                    raw_bgr = np.asarray(grabbed)[:, :, :3]
                    ts = time.monotonic()

                    # Push to worker queue; drop oldest if backlog
                    try:
                        self._raw_queue.put_nowait((ts, raw_bgr))
                    except queue.Full:
                        try:
                            self._raw_queue.get_nowait()
                            self._raw_queue.put_nowait((ts, raw_bgr))
                        except (queue.Empty, queue.Full):
                            pass

                    count += 1
                    elapsed = time.monotonic() - t0
                    if elapsed >= 1.5:
                        self.actual_fps = count / elapsed
                        count, t0 = 0, time.monotonic()
        except Exception as e:  # noqa: BLE001
            self.error = str(e)
