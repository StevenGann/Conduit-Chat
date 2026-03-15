@echo off
cd /d "%~dp0"

set SECRET_KEY=dev-secret-key-min-32-characters
set DEFAULT_PASSWORD=changeme
set SERVE_WEB_APP=true
set WEB_APP_PATH=../web

cd server
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m uvicorn conduit.main:app --reload --host 0.0.0.0 --port 8080
) else (
  py -3.12 -m uvicorn conduit.main:app --reload --host 0.0.0.0 --port 8080
)
pause
