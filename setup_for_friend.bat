@echo off
title Unicode Assignment Studio - Easy Setup
cd /d "%~dp0"
cls
echo =====================================================================
echo    UNICODE ASSIGNMENT STUDIO - AUTOMATIC SETUP
echo =====================================================================
echo.
echo Checking Python packages...
python -m pip install -r requirements.txt
echo.
echo =====================================================================
echo Setup mukammal ho gaya hai! Studio start kiya ja raha hai...
echo =====================================================================
pause

python start_server.py
