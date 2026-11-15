@echo off
chcp 65001 >nul
title Subir Proyecto a GitHub (MayAn122/Auto_reel)
color 0A

cd /d "C:\Users\piade\Desktop\Proyecto"

echo ========================================================
echo     SUBIENDO BOT A GITHUB (MayAn122/Auto_reel)
echo ========================================================
echo.

if not exist ".git" (
    git init
    git branch -M main
)

git config user.name "MayAn122"
git config user.email "MayAn122@users.noreply.github.com"

git add AUTO_REEL.py BOT_NUBE.py extraer_sesion_nube.py historial_bot.json requirements.txt .gitignore .github/ assets/ GUIA_PROCESO_REELS.md HACER_REEL.bat EXTRAER_SESION_IG.bat SUBIR_A_GITHUB.bat
git commit -m "chore: configurar bot automatico TikTok a Instagram en la nube" 2>nul

git remote remove origin 2>nul
git remote add origin "https://MayAn122@github.com/MayAn122/Auto_reel.git"

echo  Si se abre una ventana de GitHub, dale al boton verde "Sign in with your browser"
echo  y autoriza con tu cuenta MayAn122...
echo.

git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   SUBIDO CON EXITO A https://github.com/MayAn122/Auto_reel !
    echo   Ahora solo agrega el Secret IG_SESSIONID en:
    echo   Settings -^> Secrets and variables -^> Actions en tu GitHub.
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo   Hubo un error al subir. Verifica que el repositorio
    echo   se llame exactamente Auto_reel en tu cuenta MayAn122.
    echo ========================================================
)

echo.
pause
