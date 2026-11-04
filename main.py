"""Screen Clipper entry point."""
import ctypes
import sys
import winreg

from PySide6.QtWidgets import QApplication

from hotkeys import HotkeyManager
from icon import make_icon
from service import ClipService
from settings import APP_NAME, Settings
from ui import QSS, MainWindow

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_autostart(enabled: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enabled and getattr(sys, "frozen", False):
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, f'"{sys.executable}" --minimized')
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
    except OSError:
        pass


def main():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\ScreenClipperSingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # already running
        ctypes.windll.user32.MessageBoxW(0, "Screen Clipper is already running (check the system tray).",
                                         "Screen Clipper", 0x40)
        return 0
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ScreenClipper.App")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Screen Clipper")
    app.setWindowIcon(make_icon())
    app.setStyleSheet(QSS)

    settings = Settings.load()
    service = ClipService(settings)
    service.apply(settings)
    hotkeys = HotkeyManager()
    win = MainWindow(settings, service, hotkeys, set_autostart)
    if not (settings.start_minimized or "--minimized" in sys.argv):
        win.show()
    code = app.exec()
    hotkeys.stop()
    service.shutdown()
    del mutex
    return code


if __name__ == "__main__":
    sys.exit(main())

