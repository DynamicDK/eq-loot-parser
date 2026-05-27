@echo off
REM Build a standalone Windows executable. The result (dist\eq-loot-viewer.exe)
REM runs with no Python or other tools installed.
REM
REM One-time setup:  python -m pip install pyinstaller

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is not installed. Run:  python -m pip install pyinstaller
    pause
    exit /b 1
)

python -m PyInstaller --onefile --windowed --name eq-loot-viewer --clean eq_loot_gui.py
if errorlevel 1 (
    echo.
    echo Build FAILED.
    pause
    exit /b 1
)

echo.
echo Done. Executable: dist\eq-loot-viewer.exe
pause
