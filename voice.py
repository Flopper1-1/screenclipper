"""Voice trigger recognition engine using Vosk and microphone audio."""
import json
import os
import queue
import shutil
import sys
import threading
import time
import urllib.request
import zipfile

import numpy as np
from PySide6.QtCore import QObject, Signal

try:
    import vosk
    vosk.SetLogLevel(-1)
except Exception:  # noqa: BLE001
    vosk = None

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"


def get_default_model_dir() -> str:
    # 1. PyInstaller bundled path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "model")
        if os.path.exists(bundled):
            return bundled

    # 2. Local directory next to source
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
    if os.path.exists(local):
        return local

    # 3. User AppData
    appdata = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ScreenClipper", "model")
    return appdata


class VoiceEngine(QObject):
    triggered = Signal(str, int)  # phrase, duration
    status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.enabled = False
        self.triggers = []  # list of {"phrase": str, "duration": int, "enabled": bool}
        self.cooldown = 3.0
        self._last_trigger_time = 0.0

        self._model = None
        self._recognizer = None
        self._audio_queue = queue.Queue(maxsize=100)
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._grammar_lock = threading.Lock()
        self.is_ready = False

    def start(self):
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
            self._worker_thread = None

    def update_config(self, enabled: bool, triggers: list):
        with self._grammar_lock:
            self.enabled = enabled
            self.triggers = [dict(t) for t in triggers]
            self._rebuild_grammar()

    def feed_pcm(self, raw_bytes: bytes, rate: int, channels: int):
        """Called by microphone callback. Drops chunk if queue is full."""
        if not self.enabled or not self.is_ready:
            return
        try:
            self._audio_queue.put_nowait((raw_bytes, rate, channels))
        except queue.Full:
            pass

    def _ensure_model(self) -> str:
        model_path = get_default_model_dir()
        if os.path.exists(model_path) and os.path.isdir(model_path):
            return model_path

        self.status_changed.emit("Downloading voice model (one-time setup)...")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        zip_path = model_path + "_temp.zip"
        urllib.request.urlretrieve(MODEL_URL, zip_path)

        temp_extract = model_path + "_extract"
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_extract)

        extracted_sub = [
            d for d in os.listdir(temp_extract) if os.path.isdir(os.path.join(temp_extract, d))
        ][0]
        shutil.move(os.path.join(temp_extract, extracted_sub), model_path)
        os.remove(zip_path)
        shutil.rmtree(temp_extract, ignore_errors=True)
        return model_path

    def _rebuild_grammar(self):
        if not self._recognizer or not self._model:
            return
        active_phrases = [
            t["phrase"].strip().lower()
            for t in self.triggers
            if t.get("enabled", True) and t.get("phrase", "").strip()
        ]
        if not active_phrases:
            active_phrases = ["clip that"]
        grammar_json = json.dumps(active_phrases + ["[unk]"])
        try:
            self._recognizer.SetGrammar(grammar_json)
        except Exception:  # noqa: BLE001
            pass

    def _run_loop(self):
        if vosk is None:
            self.status_changed.emit("Vosk not installed")
            return

        try:
            model_dir = self._ensure_model()
            self._model = vosk.Model(model_dir)
            active_phrases = [
                t["phrase"].strip().lower()
                for t in self.triggers
                if t.get("enabled", True) and t.get("phrase", "").strip()
            ]
            if not active_phrases:
                active_phrases = ["clip that"]
            grammar_json = json.dumps(active_phrases + ["[unk]"])
            self._recognizer = vosk.KaldiRecognizer(self._model, 16000, grammar_json)
            self.is_ready = True
            self.status_changed.emit("Voice clipping active")
        except Exception as e:  # noqa: BLE001
            self.status_changed.emit(f"Voice model error: {e}")
            return

        while not self._stop_event.is_set():
            try:
                raw_bytes, rate, channels = self._audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if not self.enabled:
                continue

            # Downsample to 16kHz mono 16-bit
            try:
                data = np.frombuffer(raw_bytes, dtype=np.int16)
                if channels > 1:
                    data = data.reshape(-1, channels)[:, 0]

                if rate == 48000:
                    data_16k = data[::3]
                elif rate == 16000:
                    data_16k = data
                else:
                    target_len = int(len(data) * 16000 / rate)
                    if target_len < 1:
                        continue
                    data_16k = np.interp(
                        np.linspace(0, len(data), target_len, endpoint=False),
                        np.arange(len(data)),
                        data
                    ).astype(np.int16)

                chunk = data_16k.tobytes()
            except Exception:  # noqa: BLE001
                continue

            with self._grammar_lock:
                if self._recognizer.AcceptWaveform(chunk):
                    res = json.loads(self._recognizer.Result())
                    text = res.get("text", "").strip().lower()
                    if text:
                        self._match_phrase(text)
                else:
                    partial = json.loads(self._recognizer.PartialResult()).get("partial", "").strip().lower()
                    if partial:
                        self._match_phrase(partial)

    def _match_phrase(self, text: str):
        now = time.monotonic()
        if now - self._last_trigger_time < self.cooldown:
            return

        words_in_text = set(text.split())
        for trigger in self.triggers:
            if not trigger.get("enabled", True):
                continue
            phrase = trigger.get("phrase", "").strip().lower()
            if not phrase:
                continue

            phrase_words = phrase.split()
            # Direct substring or exact word sequence match
            if phrase in text or all(w in words_in_text for w in phrase_words):
                self._last_trigger_time = now
                try:
                    self._recognizer.Reset()
                except Exception:  # noqa: BLE001
                    pass
                duration = int(trigger.get("duration", 30))
                self.triggered.emit(trigger.get("phrase", ""), duration)
                break
