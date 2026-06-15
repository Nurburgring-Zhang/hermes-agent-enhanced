@echo off
REM Hermes - Windows Quick Install (via WSL)
REM Run this from Windows Command Prompt or double-click

echo ============================================
echo  Hermes - Windows Installer
echo ============================================
echo.

REM Check if WSL is available
wsl --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] WSL2 not found. Please install WSL2 first:
    echo   wsl --install
    echo.
    pause
    exit /b 1
)

echo [OK] WSL2 detected
echo.
echo Starting installation in WSL...
echo.

REM Get the directory of this script
set SCRIPT_DIR=%~dp0

REM Convert Windows path to WSL path
for /f "delims=" %%i in ('wsl wslpath "%SCRIPT_DIR%"') do set WSL_DIR=%%i

REM Run the bash install script inside WSL
wsl bash -c "cd '%WSL_DIR%' && bash install.sh"

echo.
echo Installation complete! Press any key to exit.
pause >nul
