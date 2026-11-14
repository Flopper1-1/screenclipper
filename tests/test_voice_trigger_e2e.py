"""Test end-to-end voice triggering and custom duration clipping."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PySide6.QtCore import QCoreApplication
from service import ClipService
from settings import Settings
from voice import VoiceEngine

app = QCoreApplication([])

# 1. Test Settings voice triggers
s = Settings()
assert len(s.voice_triggers) >= 3
s.voice_clipping_enabled = True
s.voice_triggers.append({"phrase": "headshot", "duration": 20, "enabled": True})
assert s.max_buffer_duration() >= 45
print("Settings voice config: OK")

# 2. Test VoiceEngine config update
ve = VoiceEngine()
ve.update_config(True, s.voice_triggers)
assert len(ve.triggers) == len(s.voice_triggers)
assert ve.enabled is True
print("VoiceEngine update_config: OK")

# 3. Test phrase matching logic and signal emission
received = []
ve.triggered.connect(lambda phrase, dur: received.append((phrase, dur)))

# Simulate phrase match
ve._match_phrase("what a shot")
assert len(received) == 1
assert received[0] == ("what a shot", 45)
print("VoiceEngine match phrase: OK ->", received[0])

# Verify cooldown prevents immediate duplicate trigger
ve._match_phrase("what a shot")
assert len(received) == 1, "Cooldown failed to debounce duplicate trigger"
print("VoiceEngine cooldown debounce: OK")

# Test custom duration on ClipService
svc = ClipService(s)
clip_calls = []
svc.save_clip = lambda duration=None, reason="": clip_calls.append((duration, reason))
svc._on_voice_triggered("headshot", 20)
assert len(clip_calls) == 1
assert clip_calls[0] == (20, "voice: headshot")
print("ClipService voice dispatch with duration: OK ->", clip_calls[0])

print("\nALL VOICE CLIPPING TESTS PASSED!")
