import urllib.request
import zipfile
import os
import shutil

project_dir = r"C:\Users\pierr\.gemini\antigravity\scratch\screen-clipper"
model_dir = os.path.join(project_dir, "model")

if not os.path.exists(model_dir):
    print("Downloading vosk small model...")
    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    zip_path = os.path.join(project_dir, "model_temp.zip")
    urllib.request.urlretrieve(url, zip_path)
    print("Extracting...")
    temp_dir = os.path.join(project_dir, "temp_model")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(temp_dir)
    extracted = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))][0]
    shutil.move(os.path.join(temp_dir, extracted), model_dir)
    os.remove(zip_path)
    shutil.rmtree(temp_dir)

print("Model ready at:", model_dir)
import vosk
vosk.SetLogLevel(-1)
model = vosk.Model(model_dir)
grammar = '["clip that", "save clip", "what a shot", "[unk]"]'
rec = vosk.KaldiRecognizer(model, 16000, grammar)
print("Vosk KaldiRecognizer initialized successfully with grammar!")
