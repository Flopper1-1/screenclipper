import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PySide6.QtWidgets import QApplication
from hotkeys import HotkeyManager
from service import ClipService
from settings import Settings
from ui import QSS, MainWindow

out = sys.argv[1]
app = QApplication([])
app.setStyleSheet(QSS)
s = Settings()
svc = ClipService(s)
hk = HotkeyManager()
w = MainWindow(s, svc, hk, lambda e: None)
w.show()
w.dashboard.set_last(r"C:\Users\you\Videos\ScreenClipper\Clip_2026-11-01_20-40-34.mp4")
for i, name in enumerate(["dashboard", "clips", "settings"]):
    w._goto(i)
    app.processEvents()
    w.grab().save(os.path.join(out, f"{name}.png"))
print("ok")
w.quit_app() if False else hk.stop()

