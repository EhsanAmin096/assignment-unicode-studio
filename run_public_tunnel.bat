@echo off
title Unicode Studio - Direct Public Online Link
cd /d "%~dp0"
cls
echo =====================================================================
echo    UNICODE STUDIO - DIRECT PUBLIC ONLINE LINK (ZERO SETUP)
echo =====================================================================
echo.
echo Connecting to secure online tunnel...
echo (Is window ko band mat kijiyega, minimize kar ke rakh dein)
echo.
echo =====================================================================
echo Neechay jo "https://xxxx.app.lhr.life" link aye ga:
echo Woh link copy kar ke kisi ko bhi bhej dein!
echo.
echo [!] Kisi ko kuch bhi install karne ki zaroorat nahi hai.
echo Link par click karte hi direct poori app khul jaye gi!
echo =====================================================================
echo.

ssh -R 80:127.0.0.1:8080 -o StrictHostKeyChecking=no nokey@localhost.run

echo.
echo Tunnel band ho gaya hai. Dobara chalane ke liye koi bhi key dabayein...
pause
