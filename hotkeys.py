"""Global hotkeys via the Win32 RegisterHotKey API."""
import ctypes
import threading
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012

_NAMED = {
    "Space": 0x20, "Return": 0x0D, "Enter": 0x0D, "Tab": 0x09, "Backspace": 0x08,
    "Esc": 0x1B, "Escape": 0x1B, "Home": 0x24, "End": 0x23, "PgUp": 0x21, "PgDown": 0x22,
    "Ins": 0x2D, "Del": 0x2E, "Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28,
    "Pause": 0x13, "Print": 0x2C, "ScrollLock": 0x91,
}


def parse_hotkey(text: str):
    """'Ctrl+Shift+F9' -> (modifiers, vk). Raises ValueError when invalid."""
    mods, vk = 0, None
    for part in [p.strip() for p in text.split("+") if p.strip()]:
        low = part.lower()
        if low in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif low == "alt":
            mods |= MOD_ALT
        elif low == "shift":
            mods |= MOD_SHIFT
        elif low in ("meta", "win"):
            mods |= MOD_WIN
        elif part in _NAMED:
            vk = _NAMED[part]
        elif len(part) >= 2 and part[0] in "Ff" and part[1:].isdigit() and 1 <= int(part[1:]) <= 24:
            vk = 0x6F + int(part[1:])
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        else:
            raise ValueError(f"Unsupported key: {part}")
    if vk is None:
        raise ValueError("No key in hotkey")
    return mods, vk


class HotkeyManager(QObject):
    """Registers named hotkeys on a dedicated message-loop thread."""
    triggered = Signal(str)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self._thread = None
        self._tid = None

    def register(self, bindings: dict):
        """bindings: {name: 'Ctrl+F9'}. Replaces any previous registration."""
        self.stop()
        ready = threading.Event()
        self._thread = threading.Thread(target=self._loop, args=(dict(bindings), ready), daemon=True)
        self._thread.start()
        ready.wait(2)

    def stop(self):
        if self._thread and self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            self._thread.join(timeout=2)
        self._thread, self._tid = None, None

    def _loop(self, bindings, ready):
        self._tid = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # create the message queue
        ids = {}
        for i, (name, text) in enumerate(bindings.items(), start=1):
            try:
                mods, vk = parse_hotkey(text)
                if user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, vk):
                    ids[i] = name
                else:
                    self.failed.emit(f"'{text}' is already used by another program.")
            except ValueError as e:
                self.failed.emit(str(e))
        ready.set()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam in ids:
                self.triggered.emit(ids[msg.wParam])
        for i in ids:
            user32.UnregisterHotKey(None, i)

