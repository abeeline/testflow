@echo off
setlocal
chcp 65001 >nul
title TestFlow
cd /d "%~dp0"
set "ROOT=%~dp0"

rem Windows release: app\ + python\ next to this file. Source checkout: run.py next to this file.
set "APP=%ROOT%app"
if not exist "%APP%\run.py" set "APP=%ROOT%."

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONNOUSERSITE=1"
set "PYTHONHOME="
set "PYTHONPATH="
if not defined TESTFLOW_DATA_DIR set "TESTFLOW_DATA_DIR=%ROOT%data"

set "PY=%ROOT%python\python.exe"
if exist "%PY%" goto run

rem No bundled Python: create .venv with the system Python (first run only).
set "PY=%ROOT%.venv\Scripts\python.exe"
if exist "%PY%" goto run
echo [TestFlow] First run: creating .venv and installing dependencies...
where py >nul 2>nul && (py -3 -m venv "%ROOT%.venv") || (python -m venv "%ROOT%.venv")
if not exist "%PY%" goto nopython
"%PY%" -m pip install -r "%APP%\requirements.txt"
if errorlevel 1 goto failed

:run
"%PY%" "%APP%\run.py" %*
if errorlevel 1 goto failed
goto end

:nopython
echo [TestFlow] Python 3.10+ not found. Please use the Windows release package, or install Python first.
pause
exit /b 1

:failed
echo.
echo [TestFlow] Exited with an error. See the messages above.
pause
exit /b 1

:end
endlocal
