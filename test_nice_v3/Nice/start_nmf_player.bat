@echo off
setlocal

cd /d "%~dp0"

set "PORT=6797"
set "URL=http://127.0.0.1:%PORT%/"

echo Starting NICE NMF Browser Player...
echo URL: %URL%
echo.

start "" "http://127.0.0.1:%PORT%/"
python -B "%~dp0nmf_web_player\server.py" %PORT%

endlocal
