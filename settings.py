"""Persistent user settings for Screen Clipper."""
import json
import os
from dataclasses import dataclass, asdict, fields

APP_NAME = "ScreenClipper"
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
SETTINGS_PATH = os.path.join(APPDATA_DIR, "settings.json")
THUMB_DIR = os.path.join(APPDATA_DIR, "thumbs")

RESOLUTIONS = {"Native": 0, "1440p": 1440, "1080p": 1080, "720p": 720, "480p": 480}
FPS_CHOICES = [15, 30, 60]
QUALITY_CRF = {"Low": 28, "Medium": 23, "High": 18}


def default_save_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Videos", APP_NAME)


@dataclass
class Settings:
    clip_length: int = 30
    resolution: str = "1080p"
    fps: int = 30
    quality: str = "Medium"
    save_hotkey: str = "F9"
    toggle_hotkey: str = "F10"
    monitor: int = 1
    save_dir: str = ""
    filename_template: str = "Clip_%Y-%m-%d_%H-%M-%S"
    system_audio: bool = True
    mic_audio: bool = False
    system_volume: int = 100
    mic_volume: int = 100
    start_with_windows: bool = False
    start_minimized: bool = False
    notify: bool = True
    sound: bool = True

    def __post_init__(self):
        if not self.save_dir:
            self.save_dir = default_save_dir()

    @classmethod
    def load(cls) -> "Settings":
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            names = {f.name for f in fields(cls)}
            return cls(**{k: v for k, v in data.items() if k in names})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        os.makedirs(APPDATA_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def video_restart_key(self):
        return (self.resolution, self.fps, self.monitor)

    def audio_restart_key(self):
        return (self.system_audio, self.mic_audio)

