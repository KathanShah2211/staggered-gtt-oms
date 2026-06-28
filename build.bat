@echo off
REM ============================================================
REM  build.bat — Build StaggeredGTT_OMS.exe with PyInstaller
REM ============================================================
REM  Prerequisites:
REM    pip install -r requirements.txt
REM
REM  Run from the project root directory:
REM    build.bat
REM ============================================================

echo.
echo  ██████╗ ████████╗████████╗     ██████╗ ███╗   ███╗███████╗
echo  ██╔════╝╚══██╔══╝╚══██╔══╝    ██╔═══██╗████╗ ████║██╔════╝
echo  ██║  ███╗  ██║      ██║       ██║   ██║██╔████╔██║███████╗
echo  ██║   ██║  ██║      ██║       ██║   ██║██║╚██╔╝██║╚════██║
echo  ╚██████╔╝  ██║      ██║       ╚██████╔╝██║ ╚═╝ ██║███████║
echo   ╚═════╝   ╚═╝      ╚═╝        ╚═════╝ ╚═╝     ╚═╝╚══════╝
echo.
echo  Staggered GTT OMS — Windows EXE Builder
echo  ============================================================
echo.

REM Ensure data directory exists in the build source
if not exist "data" mkdir data
if not exist "data\logs" mkdir data\logs

REM Run PyInstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "StaggeredGTT_OMS" ^
    --add-data "data;data" ^
    --hidden-import "customtkinter" ^
    --hidden-import "breeze_connect" ^
    --hidden-import "cryptography" ^
    --hidden-import "core.database" ^
    --hidden-import "core.encryption" ^
    --hidden-import "core.breeze_client" ^
    --hidden-import "core.gtt_engine" ^
    --hidden-import "ui.app" ^
    --hidden-import "ui.login_screen" ^
    --hidden-import "ui.client_manager" ^
    --hidden-import "ui.session_panel" ^
    --hidden-import "ui.holdings_panel" ^
    --hidden-import "ui.config_panel" ^
    --hidden-import "ui.preview_matrix" ^
    --hidden-import "ui.execution_panel" ^
    --hidden-import "ui.logs_panel" ^
    --hidden-import "ui.dashboard_panel" ^
    --hidden-import "ui.analysis_panel" ^
    --hidden-import "ui.suggest_panel" ^
    --hidden-import "ui.sentiment_panel" ^
    --hidden-import "ui.ai_settings_panel" ^
    --hidden-import "utils.logger" ^
    --collect-data "customtkinter" ^
    main.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo  [SUCCESS] Build complete!
    echo  Output: dist\StaggeredGTT_OMS.exe
    echo.
    echo  NOTE: Copy the 'data' folder next to the .exe before first launch,
    echo        or run the .exe from the project root directory.
) else (
    echo  [ERROR] Build failed. Check output above for details.
)
echo.
pause
