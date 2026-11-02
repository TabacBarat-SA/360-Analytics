@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 iniciar.py) || (python iniciar.py)
pause
