@echo off
echo Starting NovaMart AI Refund Agent...

start "Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak > nul
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo If Python is not found, run setup first:
echo   cd backend
echo   C:\Users\divya\anaconda3\python.exe -m venv .venv
echo   .venv\Scripts\pip install -r requirements.txt
