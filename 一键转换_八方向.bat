@echo off
chcp 65001 >nul 2>nul
cd /d "%~dp0"
title Metal Max 3 8-direction fix
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "mm3_8dir.py" %*
    goto done
)
where python >nul 2>nul
if %errorlevel%==0 (
    python "mm3_8dir.py" %*
    goto done
)
where python3 >nul 2>nul
if %errorlevel%==0 (
    python3 "mm3_8dir.py" %*
    goto done
)

echo.
echo [ERROR] Python 3 not found.
echo Please install Python 3.8 or newer and tick "Add Python to PATH":
echo     https://www.python.org/downloads/

:done
echo.
pause
