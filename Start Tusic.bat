@echo off
cd /d "%~dp0"
if exist "%~dp0dist\v0.3.1\Tusic.exe" (
    start "" "%~dp0dist\v0.3.1\Tusic.exe"
    exit /b 0
)
if exist "%~dp0dist\v0.3.0\Tusic.exe" (
    start "" "%~dp0dist\v0.3.0\Tusic.exe"
    exit /b 0
)
if exist "%~dp0dist\v0.2.0\Tusic.exe" (
    start "" "%~dp0dist\v0.2.0\Tusic.exe"
    exit /b 0
)
if exist "%~dp0dist\Tusic.exe" (
    start "" "%~dp0dist\Tusic.exe"
    exit /b 0
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 main.py
    if errorlevel 1 pause
    exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
    python main.py
    if errorlevel 1 pause
    exit /b
)
echo Install Python 3.10 or newer from python.org with Tcl/Tk enabled.
echo Or use the standalone Tusic.exe, which does not need Python.
pause
