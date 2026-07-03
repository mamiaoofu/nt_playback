@echo off
setlocal

cd /d "%~dp0"

set "PORT=8797"

echo Starting NICE NMF API Converter...
echo Service URL: http://127.0.0.1:%PORT%/
echo.

python -B "%~dp0server.py" %PORT%

endlocal
