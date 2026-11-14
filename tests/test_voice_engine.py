import json
import time
import numpy as np
import vosk

model_dir = r"C:\Users\pierr\.gemini\antigravity\scratch\screen-clipper\model"
vosk.SetLogLevel(-1)
model = vosk.Model(model_dir)

triggers = [
    {"phrase": "clip that", "duration": 30, "enabled": True},
    {"phrase": "save that", "duration": 15, "enabled": True},
    {"phrase": "what a shot", "duration": 60, "enabled": False},
]

active_phrases = [t["phrase"].lower() for t in triggers if t["enabled"]]
grammar = json.dumps(active_phrases + ["[unk]"])
rec = vosk.KaldiRecognizer(model, 16000, grammar)

print("Active phrases:", active_phrases)
print("Grammar:", grammar)

# Verify grammar can be updated dynamically
triggers.append({"phrase": "record this", "duration": 45, "enabled": True})
new_phrases = [t["phrase"].lower() for t in triggers if t["enabled"]]
rec.SetGrammar(json.dumps(new_phrases + ["[unk]"]))
print("Updated grammar:", new_phrases)
