@echo off
setlocal

REM Usa un path di Windows, non WSL, altrimenti IF EXIST fallisce
set "WIN_DIR=C:\Users\paolo\ProgettoIAPDDL"

if exist "%WIN_DIR%" (
    echo ✅ Directory trovata: %WIN_DIR%
    REM Lancia VSCode nel contesto WSL, usando path WSL
    wsl bash -c "cd /mnt/c/Users/paolo/ProgettoIAPDDL && code ."
) else (
    echo ❌ Directory non trovata: %WIN_DIR%
    pause
)
