@echo off
title Hacer Reel
color 0A

echo ============================================
echo            HACER REEL
echo ============================================
echo.

set "URL="
set "SERIE="
set "PARTE="

set /p URL=  1) Pega el link del video: 
echo.
set /p SERIE=  2) Nombre de la serie: 
echo.
set /p PARTE=  3) Numero de parte (Enter = 1): 

if "%PARTE%"=="" set "PARTE=1"

echo.
echo --------------------------------------------
echo  Serie: %SERIE%   ^|   Parte: %PARTE%
echo --------------------------------------------
echo.

"C:\Users\piade\AppData\Local\Programs\Python311\python.exe" -u "C:\Users\piade\Desktop\Proyecto\AUTO_REEL.py" "%URL%" "%SERIE%" %PARTE%

echo.
echo ============================================
echo   Terminado. El video esta en Reels_Listos
echo ============================================
echo.
pause
