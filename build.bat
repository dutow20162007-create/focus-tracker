@echo off
rem Build a standalone DashFocusTracker.exe (run on Windows)
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --windowed --onefile --name DashFocusTracker ^
  --icon assets\logo.ico --add-data "assets;assets" ^
  --collect-all qfluentwidgets --collect-all PyQt6 --hidden-import pkgutil main.py
echo.
echo Done! The exe is in the dist\ folder: dist\DashFocusTracker.exe
pause
