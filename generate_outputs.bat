@echo off
setlocal

rem ---- CONFIG ----
set "PROJECT=.\CAD\<proj_name><proj_name>"
set "VENDOR=jlcpcb"
set "KICAD_BIN=C:\Program Files\KiCad\9.0\bin"
rem ----------------

rem Ensure KiCad and KiKit wrappers are on PATH
set "PATH=%KICAD_BIN%;%KICAD_BIN%\Scripts;%PATH%"

rem Always run from the batch file's directory (repo root)
cd /d "%~dp0"

echo Generating outputs for "%PROJECT%" with vendor "%VENDOR%"
python ".\build_outputs.py" --project "%PROJECT%.kicad_pro" --no-timestamp --iso --zip --kikit "%VENDOR%"

if errorlevel 1 (
  echo.
  echo Build failed. See errors above.
  endlocal & exit /b 1
)

echo Done.

endlocal

