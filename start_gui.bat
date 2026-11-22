@echo off
REM CVSF Process Simulator - starts the interface in the web browser (Windows)
cd /d "%~dp0"
set "PY="
where python >NUL 2>NUL && set "PY=python"
if not defined PY if exist "%USERPROFILE%\miniforge3\python.exe" set "PY=%USERPROFILE%\miniforge3\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\miniforge3\python.exe" set "PY=%LOCALAPPDATA%\miniforge3\python.exe"
if not defined PY if exist "%USERPROFILE%\anaconda3\python.exe" set "PY=%USERPROFILE%\anaconda3\python.exe"
if not defined PY (
  echo Python was not found. Open the Miniforge Prompt and run: streamlit run gui\app.py
  pause
  exit /b 1
)
"%PY%" -c "import streamlit, plotly" 2>NUL || "%PY%" -m pip install -r requirements.txt
"%PY%" tools\model_update.py --auto
"%PY%" -m streamlit run gui\app.py
pause
