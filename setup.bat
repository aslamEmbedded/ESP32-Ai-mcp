@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo        ESP32 Bridge MCP - Automated Setup
echo ========================================================
echo.

:: 1. Find the correct Python executable with pip (avoiding msys64/mingw python)
set "PYTHON_EXE="

py -3 -m pip --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py -3"
    goto :found_python
)

python -m pip --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :found_python
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found_python
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :found_python
)
if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
    goto :found_python
)
if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
    goto :found_python
)

:found_python
if "!PYTHON_EXE!"=="" (
    echo [ERROR] No standard Windows Python with pip was found.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: 2. Verify virtual environment health; reset if broken or created by MinGW
if exist ".venv" (
    if not exist ".venv\Scripts\pip.exe" (
        echo [NOTICE] Existing virtual environment is incomplete. Resetting...
        rmdir /s /q .venv >nul 2>&1
    ) else (
        .\.venv\Scripts\python.exe -c "import sys" >nul 2>&1
        if errorlevel 1 (
            echo [NOTICE] Virtual environment was moved or renamed. Resetting...
            rmdir /s /q .venv >nul 2>&1
        )
    )
)

echo [1/4] Preparing Python virtual environment (.venv)...
if not exist ".venv" (
    !PYTHON_EXE! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment with !PYTHON_EXE!
        pause
        exit /b 1
    )
    echo       Created fresh virtual environment.
) else (
    echo       Virtual environment is healthy.
)

echo.
echo [2/4] Installing required libraries...
.\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo       Installed: mcp, pyserial, esptool.

echo.
echo [3/4] Configuring Antigravity MCP settings...
if not exist ".agents" mkdir .agents

set "CURR_DIR=%~dp0"
set "CURR_DIR=%CURR_DIR:~0,-1%"
set "ESC_PYTHON=%CURR_DIR%\.venv\Scripts\python.exe"
set "ESC_SERVER=%CURR_DIR%\esp32_mcp.py"

set "ESC_PYTHON=!ESC_PYTHON:\=\\!"
set "ESC_SERVER=!ESC_SERVER:\=\\!"

(
echo {
echo   "mcpServers": {
echo     "esp32-bridge": {
echo       "command": "!ESC_PYTHON!",
echo       "args": [
echo         "!ESC_SERVER!"
echo       ],
echo       "env": {}
echo     }
echo   }
echo }
) > .agents\mcp_config.json

echo       Generated: .agents\mcp_config.json for this PC!

echo.
echo [4/4] Running self-test...
.\.venv\Scripts\python.exe esp32_mcp.py --test

echo.
echo ========================================================
echo  SUCCESS! ESP32 MCP Bridge is ready on this computer.
echo ========================================================
echo  Next Steps:
echo   1. Plug in your ESP32 board via USB.
echo   2. In Antigravity IDE, press Ctrl+Shift+P and select:
echo      "Developer: Reload Window"
echo   3. Start chatting: "Find my ESP32" or "Read serial logs"!
echo ========================================================
pause
