import os, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import imageio_ffmpeg
from PySide6.QtCore import QCoreApplication
from hotkeys import parse_hotkey
from capture import FrameBuffer, target_size
from service import ClipService
from settings import Settings

# unit checks
assert parse_hotkey("F9") == (0, 0x78)
assert parse_hotkey("Ctrl+Shift+K") == (0x2 | 0x4, ord("K"))
assert target_size(2560, 1440, "1080p") == (1920, 1080)
assert target_size(1920, 1080, "1440p") == (1920, 1080)
fb = FrameBuffer(); fb.max_seconds = 2
for i in range(10): fb.add(float(i), b"x")
assert fb.span() == 2.0, fb.span()
s = Settings(); s.save_dir = tempfile.mkdtemp(); s.clip_length = 5; s.resolution = "720p"; s.fps = 30
s.system_audio = True
assert Settings(**s.__dict__).clip_length == 5
print("unit ok")

app = QCoreApplication([])
svc = ClipService(s)
result = {}
svc.clip_saved.connect(lambda p: result.setdefault("ok", p))
svc.clip_failed.connect(lambda m: result.setdefault("err", m))
svc.apply(s)
time.sleep(7)
print("fps", svc.capture.actual_fps, "size", svc.capture.frame_size, "err", svc.capture.error,
      "audio err", svc.system.error)
svc.save_clip()
t = time.time()
while not result and time.time() - t < 60:
    app.processEvents(); time.sleep(0.1)
svc.shutdown()
print(result)
assert "ok" in result
out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", result["ok"]], capture_output=True, text=True).stderr
for l in out.splitlines():
    if "Duration" in l or "Stream" in l: print(l.strip())
print("size", os.path.getsize(result["ok"]))

