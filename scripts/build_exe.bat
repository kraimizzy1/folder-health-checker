@echo off
setlocal
chcp 65001 >nul
set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%"
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onefile --name FolderHealthChecker src\folder_health_checker.py
if errorlevel 1 goto :error
echo.
echo Build complete: dist\FolderHealthChecker.exe
popd
pause
exit /b 0

:error
set "RESULT=%errorlevel%"
popd
echo.
echo Build failed. Please review the messages above.
pause
exit /b %RESULT%
