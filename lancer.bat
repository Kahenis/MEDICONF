@echo off
chcp 65001 >nul
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo Python n'est pas installe ou pas dans le PATH.
    echo Installez Python 3 depuis https://www.python.org/downloads/
    echo Cochez "Add python.exe to PATH" lors de l'installation.
    pause
    exit /b 1
)
python -m pip install -r requirements.txt -q
python app.py
if errorlevel 1 pause
