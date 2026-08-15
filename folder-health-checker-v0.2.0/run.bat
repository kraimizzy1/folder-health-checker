@echo off
setlocal
chcp 65001 >nul
set "TARGET=%~1"
if not defined TARGET (
  echo 文件夹体检器（只读扫描）
  set /p "TARGET=请输入要扫描的文件夹路径: "
)
if not defined TARGET (
  echo 未输入文件夹路径。
  pause
  exit /b 1
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0folder_health_checker.py" "%TARGET%"
) else (
  python "%~dp0folder_health_checker.py" "%TARGET%"
)
set "RESULT=%errorlevel%"
echo.
if not "%RESULT%"=="0" echo 运行失败，请查看上方提示。
pause
exit /b %RESULT%
