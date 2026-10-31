@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Install the project in .venv first. See README.md.
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0tools\view_low_load.py"
if errorlevel 1 pause
