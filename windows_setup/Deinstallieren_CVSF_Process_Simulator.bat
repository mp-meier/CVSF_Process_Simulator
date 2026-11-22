@echo off
setlocal EnableExtensions
title CVSF Process Simulator - Deinstallation
set "INST=%LOCALAPPDATA%\Programs\CVSF Process Simulator"
echo.
echo  Entfernt den CVSF Process Simulator (Programmordner und Verknuepfungen):
echo    %INST%
echo  Ihre Daten (Versuchsdatenbank, Parametersaetze) in
echo    %LOCALAPPDATA%\CVSF_Process_Simulator
echo  bleiben erhalten.
echo.
choice /c JN /n /m " Fortfahren? [J/N] "
if errorlevel 2 exit /b 0
set "EPY=%INST%\env\Scripts\python.exe"
if exist "%EPY%" if exist "%INST%\app\install_desktop_app.py" "%EPY%" "%INST%\app\install_desktop_app.py" --remove
cd /d "%TEMP%"
rmdir /s /q "%INST%\app" 2>NUL
rmdir /s /q "%INST%\env" 2>NUL
del /q "%INST%\setup_log.txt" 2>NUL
echo.
echo  Deinstalliert. (Diese Datei und der leere Ordner koennen geloescht werden.)
pause
