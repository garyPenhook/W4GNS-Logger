@echo off
REM Quick-start script for W4GNS Ham Radio Logger (Windows)
REM Uses UV with Python 3.14

REM Get the directory where this script is located
cd /d "%~dp0"

REM Check if venv exists
if not exist "venv" (
    echo Virtual environment not found. Creating with Python 3.14...
    uv venv --python 3.14 venv
    echo Installing dependencies with uv...
    uv pip install --python .\venv\Scripts\python.exe -r requirements.txt
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the application
python src/main.py

pause
