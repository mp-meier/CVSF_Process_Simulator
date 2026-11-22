@echo off
setlocal EnableExtensions
title CVSF Process Simulator - Setup
set "SRC=%~dp0"
set "INST=%LOCALAPPDATA%\Programs\CVSF Process Simulator"
set "APP=%INST%\app"
set "ENV=%INST%\env"
set "LOG=%INST%\setup_log.txt"
if not exist "%INST%" mkdir "%INST%"
echo CVSF Process Simulator setup %date% %time% > "%LOG%"
echo.
echo  ===============================================================
echo   CVSF Process Simulator - Installation
echo  ===============================================================
echo   Programmordner : %INST%
echo   Benutzerdaten  : %LOCALAPPDATA%\CVSF_Process_Simulator  (bleiben erhalten)
echo   Protokoll      : %LOG%
echo.

REM ---------------------------------------------------------------- requirements
where git >NUL 2>NUL || (set "ERR=Git wurde nicht gefunden (https://git-scm.com)." & goto fail)
set "PY="
if exist "%USERPROFILE%\miniforge3\python.exe" set "PY=%USERPROFILE%\miniforge3\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\miniforge3\python.exe" set "PY=%LOCALAPPDATA%\miniforge3\python.exe"
if not defined PY if exist "%USERPROFILE%\anaconda3\python.exe" set "PY=%USERPROFILE%\anaconda3\python.exe"
if not defined PY for /f "delims=" %%p in ('where python 2^>NUL') do if not defined PY set "PY=%%p"
if not defined PY (set "ERR=Python wurde nicht gefunden (z. B. Miniforge installieren)." & goto fail)
echo Python: %PY%>>"%LOG%"
if not exist "%SRC%Daten\CVSF_Process_Simulator.bundle" (set "ERR=Daten\CVSF_Process_Simulator.bundle fehlt." & goto fail)
if not exist "%SRC%Daten\CVSF_Model.bundle" (set "ERR=Daten\CVSF_Model.bundle fehlt." & goto fail)

REM ---------------------------------------------------------------- 1 program files (software + model V01)
echo  [1/4] Programmdateien installieren ...
if exist "%APP%" rmdir /s /q "%APP%"
git clone --quiet "%SRC%Daten\CVSF_Process_Simulator.bundle" "%APP%" >>"%LOG%" 2>&1 || (set "ERR=Programmdateien konnten nicht angelegt werden." & goto fail)
git -C "%APP%" checkout --quiet main >>"%LOG%" 2>&1
git -C "%APP%" remote set-url origin https://github.com/mp-meier/CVSF_Process_Simulator.git >>"%LOG%" 2>&1
git -C "%APP%" submodule init >>"%LOG%" 2>&1
git -C "%APP%" config submodule.cvsf_model.url "%SRC%Daten\CVSF_Model.bundle"
git -C "%APP%" -c protocol.file.allow=always submodule update >>"%LOG%" 2>&1 || (set "ERR=Modellcode konnte nicht angelegt werden." & goto fail)
git -C "%APP%" config submodule.cvsf_model.url https://github.com/mp-meier/CVSF_Model.git
git -C "%APP%\cvsf_model" remote set-url origin https://github.com/mp-meier/CVSF_Model.git >>"%LOG%" 2>&1
git -C "%APP%" log -1 --oneline >>"%LOG%" 2>&1
git -C "%APP%" submodule status >>"%LOG%" 2>&1
if not exist "%APP%\install_desktop_app.py" (set "ERR=install_desktop_app.py fehlt (evtl. von einer Sicherheitssoftware entfernt)." & goto fail)
if not exist "%APP%\gui\launcher.pyw" (set "ERR=gui\launcher.pyw fehlt (evtl. von einer Sicherheitssoftware entfernt)." & goto fail)

REM ---------------------------------------------------------------- 2 own Python environment
echo  [2/4] Python-Umgebung einrichten ...
set "EPY=%ENV%\Scripts\python.exe"
if not exist "%EPY%" "%PY%" -m venv "%ENV%" >>"%LOG%" 2>&1
if not exist "%EPY%" (echo venv failed, using %PY%>>"%LOG%" & set "EPY=%PY%")

REM ---------------------------------------------------------------- 3 packages
echo  [3/4] Pakete installieren (beim ersten Mal einige Minuten) ...
"%EPY%" -m pip install --disable-pip-version-check --no-warn-script-location -r "%APP%\requirements.txt" >>"%LOG%" 2>&1 || (set "ERR=Pakete konnten nicht installiert werden (Internetverbindung?)." & goto fail)

REM ---------------------------------------------------------------- 4 shortcuts
echo  [4/4] Verknuepfungen auf dem Desktop und im Startmenue anlegen ...
"%EPY%" "%APP%\install_desktop_app.py" >>"%LOG%" 2>&1 || (set "ERR=Verknuepfungen konnten nicht angelegt werden." & goto fail)
copy /y "%SRC%Deinstallieren_CVSF_Process_Simulator.bat" "%INST%\" >NUL 2>NUL
echo [OK] setup finished>>"%LOG%"
echo.
echo  Fertig. "CVSF Process Simulator" liegt auf dem Desktop und im Startmenue.
echo.
choice /c JN /n /m " Programm jetzt starten? [J/N] "
if errorlevel 2 exit /b 0
set "PYW=%ENV%\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%EPY%"
start "" "%PYW%" "%APP%\gui\launcher.pyw"
exit /b 0

:fail
echo [ERROR] %ERR%>>"%LOG%"
echo.
echo  FEHLER: %ERR%
echo  Details im Protokoll: %LOG%
echo.
pause
exit /b 1
