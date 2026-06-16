@echo off
echo ========================================
echo   AWS Agent - Development Servers
echo ========================================
echo.
echo Starting Backend Server...
start "AWS Agent Backend" cmd /k "python main.py"
timeout /t 3 /nobreak >nul
echo.
echo Starting Frontend Server...
start "AWS Agent Frontend" cmd /k "cd frontend && npm run dev"
echo.
echo ========================================
echo Both servers are starting!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo ========================================
echo.
echo Press any key to exit this window...
pause >nul
