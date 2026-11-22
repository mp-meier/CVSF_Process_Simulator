@echo off
REM Creates the desktop and start menu shortcut "CVSF Process Simulator" (Windows).
REM Uses the Python found on PATH or a Miniforge/Anaconda installation in the user profile.
cd /d "%~dp0"
set "PY="
where python >NUL 2>NUL && set "PY=python"
if not defined PY if exist "%USERPROFILE%\miniforge3\python.exe" set "PY=%USERPROFILE%\miniforge3\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\miniforge3\python.exe" set "PY=%LOCALAPPDATA%\miniforge3\python.exe"
if not defined PY if exist "%USERPROFILE%\anaconda3\python.exe" set "PY=%USERPROFILE%\anaconda3\python.exe"
if not defined PY (
  echo Python was not found. Open the Miniforge Prompt, activate your environment and run:
  echo     python install_desktop_app.py
  pause
  exit /b 1
)
"%PY%" install_desktop_app.py
pause
