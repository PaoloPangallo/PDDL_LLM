@echo off
setlocal
set DIR="/mnt/c/Users/paolo/ProgettoIAPDDL"
if exist %DIR% (
    wsl -e bash -c "cd %DIR% && code ."
) else (
    echo ❌ Directory non trovata: %DIR%
    pause
)
