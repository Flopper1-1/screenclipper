"""Export pipeline test using synthetic frames/audio (no desktop needed)."""
import os, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import cv2, numpy as np, imageio_ffmpeg
from PySide6.QtCore import QCoreApplication
from service import ClipService
from settings import Settings

s = Settings(); s.save_dir = tempfile.mkdtemp(); s.clip_length = 5
s.system_audio = True; s.mic_audio = False
app = QCoreApplication([])
svc = ClipService(s)
result = {}
svc.clip_saved.connect(lambda p: result.setdefault("ok", p))
svc.clip_failed.connect(lambda m: result.setdefault("err", m))

base = time.monotonic() - 5.0
for i in range(150):  # 5 s @ 30 fps, 1280x720
    img = np.full((720, 1280, 3), (i * 255 // 150, 80, 200), np.uint8)
    cv2.putText(img, str(i), (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 6, (255, 255, 255), 10)
    svc.buffer.add(base + i / 30, cv2.imencode(".jpg", img)[1].tobytes())
# 440 Hz tone chunks as fake loopback audio (1024-sample chunks @ 48k)
t = np.arange(48000 * 5) / 48000
tone = np.stack([np.sin(2 * np.pi * 440 * t)] * 2, axis=1).astype(np.float32) * 0.5
for k in range(0, len(tone) - 1024, 1024):
    svc.system.chunks.append((base + (k + 1024) / 48000, tone[k:k + 1024], 48000))
svc.save_clip()
t0 = time.time()
while not result and time.time() - t0 < 60:
    app.processEvents(); time.sleep(0.1)
print(result)
assert "ok" in result
out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", result["ok"]], capture_output=True, text=True).stderr
for l in out.splitlines():
    if "Duration" in l or "Stream" in l: print(l.strip())
print("size", os.path.getsize(result["ok"]), "thumb", os.path.exists(os.path.join(os.environ["APPDATA"], "ScreenClipper", "thumbs")))

