@echo off

chcp 65001 >nul
title Logistics Compliance System - Local Demo
echo =========================================
echo   LOGISTICS COMPLIANCE SYSTEM - DEMO
echo =========================================
echo.

cd /d "%~dp0backend"

if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [INFO] Installing dependencies...
pip install --upgrade pip --quiet 2>nul
pip install fastapi uvicorn python-multipart pydantic requests PyMuPDF Pillow pytesseract --quiet 2>nul

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Exiting...
    pause
    exit /b 1
)

echo.
echo [STARTING] Backend server on port 8000...
start "Logistics-Backend" cmd /k ".venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo [WAITING] Waiting for backend to start (3 seconds)...
timeout /t 3 >nul

echo.
echo [STARTING] Frontend server on port 5500...
cd ..\frontend
start "Logistics-Frontend" cmd /k "python -m http.server 5500"

echo.
echo =========================================
echo   APPLICATION STARTED SUCCESSFULLY!
echo =========================================
echo.
echo [API Docs]      http://localhost:8000/docs
echo [Frontend UI]   http://localhost:5500
echo.
echo [DEMO STEPS]
echo 1. Open http://localhost:5500 in your browser
echo 2. Click "Charger la demo" button
echo 3. Ask questions like:
echo    - "Quels sont les Incoterms du contrat ?"
echo    - "Quelle est la date limite de livraison?"
echo    - "Quel est le montant total de la facture?"
echo.
pause