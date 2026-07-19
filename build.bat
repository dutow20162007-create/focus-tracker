@echo off
rem Build a standalone FocusTracker.exe (run on Windows)
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --windowed --onefile --name FocusTracker ^
  --collect-all qfluentwidgets main.py
echo.
echo Done! The exe is in the dist\ folder: dist\FocusTracker.exe
pause
