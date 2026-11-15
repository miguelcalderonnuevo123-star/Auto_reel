@echo off
chcp 65001 >nul
title Subir Video Elegido a Instagram Ahora
color 0E

echo ========================================================
echo    SUBIR UN VIDEO ELEGIDO (TIKTOK -^> REEL -^> INSTAGRAM)
echo ========================================================
echo.

set "URL="
set "HOOK="
set "MARCA="

set /p URL=  1) Pega el link del video de TikTok (Enter = leer de Telegram o cola_videos.txt): 
echo.
set /p HOOK=  2) Texto del Hook (Enter = sacar automatico de la descripcion): 
echo.
set /p MARCA=  3) Tapar marca de agua? [auto / arriba / abajo / no] (Enter = auto): 
echo.

if "%MARCA%"=="" set "MARCA=auto"

set "ARGS=--marca %MARCA%"
if not "%URL%"=="" set "ARGS=%ARGS% --url "%URL%""
if not "%HOOK%"=="" set "ARGS=%ARGS% --hook "%HOOK%""

"C:\Users\piade\AppData\Local\Programs\Python311\python.exe" -u "C:\Users\piade\Desktop\Proyecto\BOT_NUBE.py" %ARGS%

echo.
pause
