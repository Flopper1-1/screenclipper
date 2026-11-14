$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python icon.py app.ico
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ScreenClipper `
  --icon app.ico `
  --add-data "model;model" `
  --collect-all imageio_ffmpeg --collect-all pyaudiowpatch --collect-all vosk `
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets `
  --exclude-module PySide6.QtPdf --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml `
  --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtCharts --exclude-module PySide6.QtMultimedia `
  main.py
Copy-Item "dist\ScreenClipper.exe" "$env:USERPROFILE\Downloads\ScreenClipper.exe" -Force
Write-Host "Built: $env:USERPROFILE\Downloads\ScreenClipper.exe"
