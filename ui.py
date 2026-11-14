"""PySide6 user interface."""
import os
import subprocess
import threading
import time
import winsound
from datetime import datetime

import cv2
import mss
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from hotkeys import parse_hotkey
from icon import make_icon
from service import ClipService, thumb_path_for
from settings import FPS_CHOICES, QUALITY_CRF, RESOLUTIONS, THUMB_DIR, Settings

QSS = """
* { font-family: 'Segoe UI'; font-size: 13px; color: #e6e8ee; }
QMainWindow, QWidget#root { background: #0f1115; }
QWidget#sidebar { background: #14171d; border-right: 1px solid #222733; }
QLabel#brand { font-size: 17px; font-weight: 700; }
QPushButton#nav { text-align: left; padding: 11px 16px; border: none; border-radius: 10px;
  background: transparent; color: #9aa3b5; font-size: 14px; }
QPushButton#nav:hover { background: #1c2029; color: #e6e8ee; }
QPushButton#nav:checked { background: #272c5a; color: #ffffff; font-weight: 600; }
QFrame#card { background: #181b22; border: 1px solid #242938; border-radius: 14px; }
QLabel#h1 { font-size: 24px; font-weight: 700; }
QLabel#h2 { font-size: 15px; font-weight: 600; }
QLabel#muted { color: #8a93a6; }
QLabel#chip { background: #222737; border-radius: 8px; padding: 4px 10px; color: #c9cfe0; font-weight: 600; }
QLabel#stat { font-size: 20px; font-weight: 700; }
QPushButton { background: #232838; border: 1px solid #2d3347; border-radius: 9px; padding: 8px 16px; }
QPushButton:hover { background: #2c3248; }
QPushButton:disabled { color: #5c6478; }
QPushButton#primary { background: #5b5ff0; border: none; font-weight: 600; font-size: 15px; padding: 14px 24px; }
QPushButton#primary:hover { background: #6e72ff; }
QPushButton#danger:hover { background: #7a2631; }
QLineEdit, QComboBox, QSpinBox, QKeySequenceEdit { background: #11141a; border: 1px solid #2b3144;
  border-radius: 8px; padding: 7px 10px; min-height: 18px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QKeySequenceEdit:focus { border-color: #5b5ff0; }
QComboBox QAbstractItemView { background: #181b22; selection-background-color: #31367a; border: 1px solid #2b3144; }
QSlider::groove:horizontal { height: 6px; background: #2a3042; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #5b5ff0; border-radius: 3px; }
QSlider::handle:horizontal { background: #fff; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #3a4260; background: #11141a; }
QCheckBox::indicator:checked { background: #5b5ff0; border-color: #5b5ff0; }
QProgressBar { background: #2a3042; border: none; border-radius: 4px; max-height: 8px; }
QProgressBar::chunk { background: #5b5ff0; border-radius: 4px; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #2f364c; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #181b22; color: #e6e8ee; border: 1px solid #2b3144; }
"""


def card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    return f


def label(text, obj=None) -> QLabel:
    l = QLabel(text)
    if obj:
        l.setObjectName(obj)
    return l


def show_in_explorer(path: str):
    if os.path.exists(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    else:
        folder = os.path.dirname(path)
        if os.path.isdir(folder):
            os.startfile(folder)


def copy_text(text: str):
    QGuiApplication.clipboard().setText(text)


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def pretty_key(text: str) -> str:
    return text.replace("+", " + ") if text else "Not set"


# ---------------------------------------------------------------- dashboard
class DashboardPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.last_path = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(18)
        lay.addWidget(label("Dashboard", "h1"))

        # status card
        c = card()
        cl = QHBoxLayout(c)
        cl.setContentsMargins(24, 22, 24, 22)
        left = QVBoxLayout()
        self.status = label("", "h2")
        self.status_sub = label("", "muted")
        left.addWidget(self.status)
        left.addWidget(self.status_sub)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        left.addSpacing(6)
        left.addWidget(self.progress)
        cl.addLayout(left, 1)
        cl.addSpacing(24)
        self.save_btn = QPushButton("●  Save clip now")
        self.save_btn.setObjectName("primary")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(win.save_clip)
        cl.addWidget(self.save_btn)
        lay.addWidget(c)

        # stats
        grid = QGridLayout()
        grid.setSpacing(14)
        self.stat_len, self.stat_res, self.stat_fps, self.stat_mem = (label("-", "stat") for _ in range(4))
        for i, (title, w) in enumerate([
            ("Clip length", self.stat_len),
            ("Resolution", self.stat_res),
            ("Capture FPS", self.stat_fps),
            ("Buffer memory", self.stat_mem),
        ]):
            sc = card()
            sl = QVBoxLayout(sc)
            sl.setContentsMargins(18, 14, 18, 14)
            sl.addWidget(label(title, "muted"))
            sl.addWidget(w)
            grid.addWidget(sc, 0, i)
        lay.addLayout(grid)

        # hotkeys & voice row
        hk = card()
        hl = QHBoxLayout(hk)
        hl.setContentsMargins(24, 16, 24, 16)
        hl.addWidget(label("Save clip", "muted"))
        self.chip_save = label("", "chip")
        hl.addWidget(self.chip_save)
        hl.addSpacing(20)
        hl.addWidget(label("Pause / resume", "muted"))
        self.chip_toggle = label("", "chip")
        hl.addWidget(self.chip_toggle)
        hl.addSpacing(20)
        hl.addWidget(label("Voice trigger", "muted"))
        self.chip_voice = label("", "chip")
        hl.addWidget(self.chip_voice)
        hl.addStretch()
        self.pause_btn = QPushButton("Pause buffer")
        self.pause_btn.clicked.connect(win.toggle_pause)
        hl.addWidget(self.pause_btn)
        lay.addWidget(hk)

        # last clip
        self.last_card = card()
        ll = QVBoxLayout(self.last_card)
        ll.setContentsMargins(24, 18, 24, 18)
        ll.addWidget(label("Last saved clip", "h2"))
        self.last_name = label("No clips saved this session", "muted")
        self.last_name.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.last_name.setWordWrap(True)
        ll.addWidget(self.last_name)
        row = QHBoxLayout()
        self.btn_show = QPushButton("Show in Explorer")
        self.btn_copy = QPushButton("Copy path")
        self.btn_play = QPushButton("Play")
        for b in (self.btn_show, self.btn_copy, self.btn_play):
            b.setEnabled(False)
            row.addWidget(b)
        row.addStretch()
        ll.addLayout(row)
        self.btn_show.clicked.connect(lambda: show_in_explorer(self.last_path))
        self.btn_copy.clicked.connect(lambda: (copy_text(self.last_path), win.flash("Path copied to clipboard")))
        self.btn_play.clicked.connect(lambda: os.startfile(self.last_path))
        lay.addWidget(self.last_card)
        lay.addStretch()

    def set_last(self, path: str):
        self.last_path = path
        self.last_name.setText(path)
        for b in (self.btn_show, self.btn_copy, self.btn_play):
            b.setEnabled(True)

    def refresh(self):
        w, s = self.win, self.win.settings
        svc = w.service
        err = svc.capture.error
        if err:
            self.status.setText("⚠  Capture error")
            self.status_sub.setText(err)
        elif svc.saving:
            self.status.setText("🟡  Saving clip…")
            self.status_sub.setText("Encoding video, this takes a moment.")
        elif svc.paused:
            self.status.setText("⏸  Buffer paused")
            self.status_sub.setText("Nothing is being recorded.")
        else:
            self.status.setText("🟢  Buffering")
            self.status_sub.setText(f"The last {s.clip_length} seconds are ready to be saved.")
        span = svc.buffer.span()
        self.progress.setValue(int(min(1.0, span / max(s.clip_length, 1)) * 100))
        self.stat_len.setText(f"{s.clip_length} s")
        fw, fh = svc.capture.frame_size
        self.stat_res.setText(f"{fw}×{fh}" if fw else s.resolution)
        self.stat_fps.setText(f"{svc.capture.actual_fps:.0f} / {s.fps}")
        self.stat_mem.setText(human_size(svc.buffer.size_bytes()))
        self.chip_save.setText(pretty_key(s.save_hotkey))
        self.chip_toggle.setText(pretty_key(s.toggle_hotkey))

        if s.voice_clipping_enabled:
            active_count = sum(1 for t in s.voice_triggers if t.get("enabled", True))
            self.chip_voice.setText(f"🎙 Active ({active_count})")
        else:
            self.chip_voice.setText("🎙 Disabled")

        self.pause_btn.setText("Resume buffer" if svc.paused else "Pause buffer")
        self.save_btn.setEnabled(not svc.saving)


# -------------------------------------------------------------------- clips
class ClipRow(QFrame):
    def __init__(self, path, page):
        super().__init__()
        self.setObjectName("card")
        self.path, self.page = path, page
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(16)
        thumb = QLabel()
        thumb.setFixedSize(176, 99)
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setStyleSheet("background:#0b0d11; border-radius:8px;")
        pm = QPixmap(self._ensure_thumb())
        if not pm.isNull():
            thumb.setPixmap(pm.scaled(176, 99, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(thumb)

        info = QVBoxLayout()
        name = label(os.path.basename(path), "h2")
        info.addWidget(name)
        st = os.stat(path)
        dur = self._duration()
        meta = f"{datetime.fromtimestamp(st.st_mtime):%b %d, %Y  %H:%M}   •   {dur}   •   {human_size(st.st_size)}"
        info.addWidget(label(meta, "muted"))
        p = label(path, "muted")
        p.setTextInteractionFlags(Qt.TextSelectableByMouse)
        p.setWordWrap(True)
        info.addWidget(p)
        info.addStretch()
        btns = QHBoxLayout()
        for text, fn, obj in (
            ("Play", lambda: os.startfile(path), None),
            ("Show in Explorer", lambda: show_in_explorer(path), None),
            ("Copy path", self._copy, None),
            ("Delete", self._delete, "danger"),
        ):
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch()
        info.addLayout(btns)
        lay.addLayout(info, 1)

    def _duration(self):
        try:
            cap = cv2.VideoCapture(self.path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            return f"{n / fps:.0f} s" if fps else "-"
        except Exception:  # noqa: BLE001
            return "-"

    def _ensure_thumb(self):
        tp = thumb_path_for(self.path)
        if not os.path.exists(tp):
            try:
                os.makedirs(THUMB_DIR, exist_ok=True)
                cap = cv2.VideoCapture(self.path)
                cap.set(cv2.CAP_PROP_POS_FRAMES, (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 2) // 2)
                ok, frame = cap.read()
                cap.release()
                if ok:
                    cv2.imwrite(tp, frame)
            except Exception:  # noqa: BLE001
                pass
        return tp

    def _copy(self):
        copy_text(self.path)
        self.page.win.flash("Path copied to clipboard")

    def _delete(self):
        if QMessageBox.question(self, "Delete clip", f"Permanently delete\n{os.path.basename(self.path)}?") == QMessageBox.Yes:
            try:
                os.remove(self.path)
                tp = thumb_path_for(self.path)
                if os.path.exists(tp):
                    os.remove(tp)
            except OSError as e:
                QMessageBox.warning(self, "Delete failed", str(e))
            self.page.reload()


class ClipsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)
        head = QHBoxLayout()
        head.addWidget(label("Clips", "h1"))
        head.addStretch()
        b_open = QPushButton("Open clips folder")
        b_open.clicked.connect(lambda: os.startfile(self._folder()))
        b_ref = QPushButton("Refresh")
        b_ref.clicked.connect(self.reload)
        head.addWidget(b_open)
        head.addWidget(b_ref)
        lay.addLayout(head)
        self.folder_lbl = label("", "muted")
        self.folder_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.folder_lbl)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inner = QWidget()
        self.inner_lay = QVBoxLayout(self.inner)
        self.inner_lay.setContentsMargins(0, 0, 8, 0)
        self.inner_lay.setSpacing(12)
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll, 1)

    def _folder(self):
        d = self.win.settings.save_dir
        os.makedirs(d, exist_ok=True)
        return d

    def reload(self):
        d = self.win.settings.save_dir
        self.folder_lbl.setText(f"Saving to: {d}")
        while self.inner_lay.count():
            it = self.inner_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        files = []
        if os.path.isdir(d):
            files = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".mp4")]
        files.sort(key=os.path.getmtime, reverse=True)
        if not files:
            empty = label("No clips yet. Press your save hotkey or say a voice phrase while something is on screen.", "muted")
            empty.setAlignment(Qt.AlignCenter)
            self.inner_lay.addWidget(empty)
        for f in files[:80]:
            self.inner_lay.addWidget(ClipRow(f, self))
        self.inner_lay.addStretch()


# ----------------------------------------------------------------- settings
def section(title, sub=None):
    c = card()
    v = QVBoxLayout(c)
    v.setContentsMargins(24, 18, 24, 20)
    v.setSpacing(12)
    v.addWidget(label(title, "h2"))
    if sub:
        sl = label(sub, "muted")
        sl.setWordWrap(True)
        v.addWidget(sl)
    return c, v


def row(text, widget, hint=None):
    h = QHBoxLayout()
    l = QLabel(text)
    l.setMinimumWidth(170)
    h.addWidget(l)
    h.addWidget(widget, 1)
    if hint:
        h.addWidget(label(hint, "muted"))
    return h


class SettingsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self._voice_triggers = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 20)
        head = QHBoxLayout()
        head.addWidget(label("Settings", "h1"))
        head.addStretch()
        self.msg = label("", "muted")
        head.addWidget(self.msg)
        outer.addLayout(head)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(14)
        sa.setWidget(body)
        outer.addWidget(sa, 1)

        # recording
        c, cv = section("Recording")
        self.length = QSlider(Qt.Horizontal)
        self.length.setRange(5, 300)
        self.length_spin = QSpinBox()
        self.length_spin.setRange(5, 300)
        self.length_spin.setSuffix(" s")
        self.length.valueChanged.connect(self.length_spin.setValue)
        self.length_spin.valueChanged.connect(self.length.setValue)
        lh = QHBoxLayout()
        lh.addWidget(QLabel("Clip length"))
        lh.itemAt(0).widget().setMinimumWidth(170)
        lh.addWidget(self.length, 1)
        lh.addWidget(self.length_spin)
        cv.addLayout(lh)
        self.res = QComboBox()
        self.res.addItems(list(RESOLUTIONS))
        cv.addLayout(row("Resolution", self.res))
        self.fps = QComboBox()
        for f in FPS_CHOICES:
            self.fps.addItem(f"{f} FPS", f)
        cv.addLayout(row("Frame rate", self.fps))
        self.quality = QComboBox()
        self.quality.addItems(list(QUALITY_CRF))
        cv.addLayout(row("Quality", self.quality))
        self.monitor = QComboBox()
        with mss.mss() as sct:
            for i, m in enumerate(sct.monitors[1:], start=1):
                self.monitor.addItem(f"Monitor {i}  ({m['width']}×{m['height']})", i)
        cv.addLayout(row("Monitor", self.monitor))
        note = label("Hardware-accelerated encoding (AMD AMF / NVIDIA NVENC / Intel QSV) is auto-detected.", "muted")
        note.setWordWrap(True)
        cv.addWidget(note)
        v.addWidget(c)

        # hotkeys
        c, cv = section("Hotkeys", "Click a box and press the key combination you want.")
        self.hk_save = QKeySequenceEdit()
        self.hk_toggle = QKeySequenceEdit()
        for e in (self.hk_save, self.hk_toggle):
            e.setMaximumSequenceLength(1)
        cv.addLayout(row("Save clip", self.hk_save))
        cv.addLayout(row("Pause / resume buffer", self.hk_toggle))
        v.addWidget(c)

        # voice clipping
        c, cv = section("Voice Clipping", "Say a phrase into your microphone to automatically save a clip.")
        self.cb_voice = QCheckBox("Enable voice clipping triggers")
        cv.addWidget(self.cb_voice)

        self.voice_status_lbl = label("Status: Initializing...", "muted")
        cv.addWidget(self.voice_status_lbl)

        cv.addWidget(label("Active Voice Clippings:", "h2"))
        self.triggers_layout = QVBoxLayout()
        self.triggers_layout.setSpacing(6)
        cv.addLayout(self.triggers_layout)

        # Add new trigger row
        add_frame = QFrame()
        add_frame.setStyleSheet("background: #11141a; border-radius: 8px; padding: 6px;")
        add_lay = QHBoxLayout(add_frame)
        add_lay.setContentsMargins(6, 4, 6, 4)
        self.add_phrase_input = QLineEdit()
        self.add_phrase_input.setPlaceholderText("New trigger phrase (e.g. clip that, what a shot)...")
        self.add_dur_spin = QSpinBox()
        self.add_dur_spin.setRange(5, 300)
        self.add_dur_spin.setValue(30)
        self.add_dur_spin.setSuffix(" s")
        btn_add_trigger = QPushButton("+ Add Voice Trigger")
        btn_add_trigger.clicked.connect(self._add_trigger)
        add_lay.addWidget(self.add_phrase_input, 1)
        add_lay.addWidget(self.add_dur_spin)
        add_lay.addWidget(btn_add_trigger)
        cv.addWidget(add_frame)
        v.addWidget(c)

        # audio
        c, cv = section("Audio")
        self.sys_on = QCheckBox("Record system audio (game / desktop sound)")
        self.sys_vol = QSlider(Qt.Horizontal)
        self.sys_vol.setRange(0, 200)
        self.mic_on = QCheckBox("Record microphone in saved clip")
        self.mic_vol = QSlider(Qt.Horizontal)
        self.mic_vol.setRange(0, 200)
        cv.addWidget(self.sys_on)
        cv.addLayout(row("System volume", self.sys_vol))
        cv.addWidget(self.mic_on)
        cv.addLayout(row("Microphone volume", self.mic_vol))
        v.addWidget(c)

        # storage
        c, cv = section("Storage")
        self.folder = QLineEdit()
        b = QPushButton("Browse…")
        b.clicked.connect(self._browse)
        fh = QHBoxLayout()
        fl = QLabel("Save folder")
        fl.setMinimumWidth(170)
        fh.addWidget(fl)
        fh.addWidget(self.folder, 1)
        fh.addWidget(b)
        cv.addLayout(fh)
        self.template = QLineEdit()
        self.template.textChanged.connect(self._preview)
        cv.addLayout(row("File name", self.template, ".mp4"))
        self.preview = label("", "muted")
        cv.addWidget(self.preview)
        v.addWidget(c)

        # general
        c, cv = section("General")
        self.cb_start = QCheckBox("Start with Windows")
        self.cb_min = QCheckBox("Start minimized to tray")
        self.cb_notify = QCheckBox("Show a notification when a clip is saved")
        self.cb_sound = QCheckBox("Play a sound when a clip is saved")
        for cb in (self.cb_start, self.cb_min, self.cb_notify, self.cb_sound):
            cv.addWidget(cb)
        v.addWidget(c)
        v.addStretch()

        bar = QHBoxLayout()
        bar.addStretch()
        reset = QPushButton("Revert changes")
        reset.clicked.connect(self.load)
        save = QPushButton("Save settings")
        save.setObjectName("primary")
        save.clicked.connect(self.apply)
        bar.addWidget(reset)
        bar.addWidget(save)
        outer.addLayout(bar)
        self.load()

    def _preview(self):
        try:
            self.preview.setText("Example:  " + time.strftime(self.template.text() or "Clip") + ".mp4")
        except ValueError:
            self.preview.setText("Invalid date pattern")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Choose save folder", self.folder.text())
        if d:
            self.folder.setText(os.path.normpath(d))

    def _render_triggers(self):
        while self.triggers_layout.count():
            item = self.triggers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._voice_triggers:
            empty = label("No voice trigger phrases configured. Add one below.", "muted")
            self.triggers_layout.addWidget(empty)
            return

        for idx, trigger in enumerate(self._voice_triggers):
            row_frame = QFrame()
            row_frame.setStyleSheet("background: #151922; border-radius: 8px; border: 1px solid #232a3d;")
            rl = QHBoxLayout(row_frame)
            rl.setContentsMargins(10, 6, 10, 6)
            rl.setSpacing(12)

            cb = QCheckBox(f'💬 "{trigger.get("phrase", "")}"')
            cb.setChecked(trigger.get("enabled", True))

            def on_toggle(checked, i=idx):
                self._voice_triggers[i]["enabled"] = checked

            cb.toggled.connect(on_toggle)
            rl.addWidget(cb, 1)

            dur_spin = QSpinBox()
            dur_spin.setRange(5, 300)
            dur_spin.setValue(int(trigger.get("duration", 30)))
            dur_spin.setSuffix(" s")

            def on_dur(val, i=idx):
                self._voice_triggers[i]["duration"] = val

            dur_spin.valueChanged.connect(on_dur)
            rl.addWidget(dur_spin)

            btn_del = QPushButton("✕ Remove")
            btn_del.setObjectName("danger")

            def on_del(i=idx):
                self._voice_triggers.pop(i)
                self._render_triggers()

            btn_del.clicked.connect(on_del)
            rl.addWidget(btn_del)

            self.triggers_layout.addWidget(row_frame)

    def _add_trigger(self):
        phrase = self.add_phrase_input.text().strip().lower()
        if not phrase:
            self.msg.setText("⚠ Please enter a phrase first.")
            return
        if any(t.get("phrase", "").strip().lower() == phrase for t in self._voice_triggers):
            self.msg.setText("⚠ This phrase is already in the list.")
            return
        duration = self.add_dur_spin.value()
        self._voice_triggers.append({"phrase": phrase, "duration": duration, "enabled": True})
        self.add_phrase_input.clear()
        self._render_triggers()
        self.msg.setText("✓ Added voice trigger")

    def load(self):
        s = self.win.settings
        self.length.setValue(s.clip_length)
        self.length_spin.setValue(s.clip_length)
        self.res.setCurrentText(s.resolution)
        self.fps.setCurrentIndex(max(0, self.fps.findData(s.fps)))
        self.quality.setCurrentText(s.quality)
        self.monitor.setCurrentIndex(max(0, self.monitor.findData(s.monitor)))
        self.hk_save.setKeySequence(QKeySequence(s.save_hotkey))
        self.hk_toggle.setKeySequence(QKeySequence(s.toggle_hotkey))
        self.cb_voice.setChecked(s.voice_clipping_enabled)
        self._voice_triggers = [dict(t) for t in s.voice_triggers]
        self._render_triggers()
        self.sys_on.setChecked(s.system_audio)
        self.sys_vol.setValue(s.system_volume)
        self.mic_on.setChecked(s.mic_audio)
        self.mic_vol.setValue(s.mic_volume)
        self.folder.setText(s.save_dir)
        self.template.setText(s.filename_template)
        self.cb_start.setChecked(s.start_with_windows)
        self.cb_min.setChecked(s.start_minimized)
        self.cb_notify.setChecked(s.notify)
        self.cb_sound.setChecked(s.sound)
        self._preview()
        self.msg.setText("")

    def apply(self):
        save_hk = self.hk_save.keySequence().toString(QKeySequence.PortableText)
        tog_hk = self.hk_toggle.keySequence().toString(QKeySequence.PortableText)
        try:
            for hk in (save_hk, tog_hk):
                parse_hotkey(hk)
        except ValueError as e:
            self.msg.setText(f"⚠ Hotkey problem: {e}")
            return
        if save_hk == tog_hk:
            self.msg.setText("⚠ The two hotkeys must be different.")
            return
        s = self.win.settings
        s.clip_length = self.length.value()
        s.resolution = self.res.currentText()
        s.fps = self.fps.currentData()
        s.quality = self.quality.currentText()
        s.monitor = self.monitor.currentData() or 1
        s.save_hotkey, s.toggle_hotkey = save_hk, tog_hk
        s.voice_clipping_enabled = self.cb_voice.isChecked()
        s.voice_triggers = [dict(t) for t in self._voice_triggers]
        s.system_audio, s.system_volume = self.sys_on.isChecked(), self.sys_vol.value()
        s.mic_audio, s.mic_volume = self.mic_on.isChecked(), self.mic_vol.value()
        s.save_dir = self.folder.text().strip() or s.save_dir
        s.filename_template = self.template.text().strip() or "Clip_%Y-%m-%d_%H-%M-%S"
        s.start_with_windows, s.start_minimized = self.cb_start.isChecked(), self.cb_min.isChecked()
        s.notify, s.sound = self.cb_notify.isChecked(), self.cb_sound.isChecked()
        self.win.settings_changed()
        self.msg.setText("✓ Settings saved")


# -------------------------------------------------------------- main window
class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, service: ClipService, hotkeys, set_autostart):
        super().__init__()
        self.settings, self.service, self.hotkeys = settings, service, hotkeys
        self.set_autostart = set_autostart
        self.setWindowTitle("Screen Clipper")
        self.setWindowIcon(make_icon())
        self.resize(1060, 740)
        self.setMinimumSize(920, 640)
        self._quitting = False

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(210)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 22, 14, 18)
        sl.setSpacing(6)
        sl.addWidget(label("  Screen Clipper", "brand"))
        sl.addSpacing(16)
        self.pages = QStackedWidget()
        self.dashboard = DashboardPage(self)
        self.clips = ClipsPage(self)
        self.settings_page = SettingsPage(self)
        group = QButtonGroup(self)
        for i, (text, page) in enumerate([
            ("  🏠   Dashboard", self.dashboard),
            ("  🎞   Clips", self.clips),
            ("  ⚙   Settings", self.settings_page),
        ]):
            b = QPushButton(text)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            group.addButton(b, i)
            sl.addWidget(b)
            self.pages.addWidget(page)
        group.button(0).setChecked(True)
        group.idClicked.connect(self._goto)
        sl.addStretch()
        self.toast = label("", "muted")
        self.toast.setWordWrap(True)
        sl.addWidget(self.toast)
        q = QPushButton("Quit Screen Clipper")
        q.clicked.connect(self.quit_app)
        sl.addWidget(q)
        h.addWidget(side)
        h.addWidget(self.pages, 1)

        # tray
        self.tray = QSystemTrayIcon(make_icon(), self)
        menu = QMenu()
        menu.addAction("Open", self.show_window)
        menu.addAction("Save clip now", self.save_clip)
        menu.addAction("Pause / resume buffer", self.toggle_pause)
        menu.addSeparator()
        menu.addAction("Quit", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Screen Clipper")
        self.tray.activated.connect(lambda r: self.show_window() if r == QSystemTrayIcon.Trigger else None)
        self.tray.messageClicked.connect(self._open_last)
        self.tray.show()

        service.clip_saved.connect(self.on_saved)
        service.clip_failed.connect(self.on_failed)
        service.voice_triggered.connect(self.on_voice_triggered)
        service.voice.status_changed.connect(self.settings_page.voice_status_lbl.setText)
        hotkeys.triggered.connect(self.on_hotkey)
        hotkeys.failed.connect(lambda m: self.flash("⚠ " + m))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.dashboard.refresh)
        self.timer.start(500)
        self.dashboard.refresh()
        self.register_hotkeys()

    # ---- helpers
    def register_hotkeys(self):
        self.hotkeys.register({"save": self.settings.save_hotkey, "toggle": self.settings.toggle_hotkey})

    def _goto(self, i):
        self.pages.setCurrentIndex(i)
        if i == 1:
            self.clips.reload()
        if i == 2:  # free the hotkeys so they can be re-recorded without triggering
            self.hotkeys.stop()
        else:
            self.register_hotkeys()

    def flash(self, text):
        self.toast.setText(text)
        QTimer.singleShot(5000, lambda: self.toast.setText("") if self.toast.text() == text else None)

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def save_clip(self):
        self.service.save_clip()

    def toggle_pause(self):
        self.service.set_paused(not self.service.paused)
        self.flash("Buffer paused" if self.service.paused else "Buffer resumed")

    def on_hotkey(self, name):
        if name == "save":
            self.save_clip()
        elif name == "toggle":
            self.toggle_pause()

    def on_voice_triggered(self, phrase, duration):
        msg = f"🎙️ Voice Trigger: \"{phrase}\" ({duration}s)"
        self.flash(msg)
        if self.settings.sound:
            threading.Thread(target=lambda: winsound.Beep(1200, 150), daemon=True).start()
        if self.settings.notify:
            self.tray.showMessage("Screen Clipper Voice Trigger", msg, QSystemTrayIcon.Information, 4000)

    def on_saved(self, path):
        self.dashboard.set_last(path)
        self.flash("Clip saved")
        if self.settings.notify:
            self._last_path = path
            self.tray.showMessage("Clip saved", path, QSystemTrayIcon.Information, 5000)
        if self.settings.sound:
            threading.Thread(target=lambda: winsound.Beep(1100, 140), daemon=True).start()
        if self.pages.currentIndex() == 1:
            self.clips.reload()

    def on_failed(self, msg):
        self.flash("⚠ " + msg)
        if self.settings.notify:
            self.tray.showMessage("Screen Clipper", msg, QSystemTrayIcon.Warning, 5000)

    def _open_last(self):
        if self.dashboard.last_path:
            show_in_explorer(self.dashboard.last_path)

    def settings_changed(self):
        self.settings.save()
        self.set_autostart(self.settings.start_with_windows)
        self.service.apply(self.settings)
        self.dashboard.refresh()

    def quit_app(self):
        self._quitting = True
        self.hotkeys.stop()
        self.service.shutdown()
        self.tray.hide()
        QGuiApplication.quit()

    def closeEvent(self, e):
        if self._quitting or not self.tray.isVisible():
            e.accept()
        else:
            e.ignore()
            self.hide()
            if not getattr(self, "_told", False):
                self._told = True
                self.tray.showMessage(
                    "Screen Clipper is still running",
                    f"Press {self.settings.save_hotkey} to save a clip. Quit from the tray icon.",
                    QSystemTrayIcon.Information,
                    4000,
                )
