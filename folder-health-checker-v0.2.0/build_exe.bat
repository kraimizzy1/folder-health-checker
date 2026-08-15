@echo off
setlocal
chcp 65001 >nul
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --name FolderHealthChecker folder_health_checker.py
echo.
echo Build complete: dist\FolderHealthChecker.exe
pause
