@echo off
title Unicode Studio - Online Public Link
cd /d "%~dp0"
cls
echo =====================================================================
echo    UNICODE STUDIO - ONLINE LINK (DIFFERENT WI-FI / INTERNET)
echo =====================================================================
echo.
echo Connecting to secure online tunnel...
echo.
echo [!] NOTE: Is black window ko khula rehne dein (minimize kar lein).
echo Neechay jo "https://...pinggy-free.link" aye ga, woh link dost ko bhej dein.
echo Dost jab link kholega to sirf aik baar "Enter site" par click kare ga,
echo aur aap ki poori Assignment Studio app uske paas chal pare gi!
echo =====================================================================
echo.

ssh -p 443 -R0:localhost:8080 -o StrictHostKeyChecking=no a.pinggy.io

echo.
echo Tunnel band ho gaya hai.
pause
