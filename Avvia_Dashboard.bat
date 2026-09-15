@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Avvia_Dashboard.ps1"
if errorlevel 1 (
  echo.
  echo Avvio non riuscito. Leggi il messaggio qui sopra.
  pause
)
endlocal
