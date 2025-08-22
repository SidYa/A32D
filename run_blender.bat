@echo off
chcp 65001 >nul
echo Starting 3D to 2D Animation Exporter...
echo.

REM Find Blender installation
set "BLENDER_PATH="

REM Check Program Files directories
for /d %%i in ("%ProgramFiles%\Blender Foundation\Blender *") do (
    if exist "%%i\blender.exe" (
        set "BLENDER_PATH=%%i\blender.exe"
        goto FOUND_BLENDER
    )
)

REM Check Program Files (x86) for 32-bit Blender on 64-bit Windows
for /d %%i in ("%ProgramFiles(x86)%\Blender Foundation\Blender *") do (
    if exist "%%i\blender.exe" (
        set "BLENDER_PATH=%%i\blender.exe"
        goto FOUND_BLENDER
    )
)

REM Check registry for installed versions
for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\blender.exe" /ve 2^>nul ^| find "REG_SZ"') do (
    if exist "%%~b" (
        set "BLENDER_PATH=%%~b"
        goto FOUND_BLENDER
    )
)

REM Check for per-user installation
for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\blender.exe" /ve 2^>nul ^| find "REG_SZ"') do (
    if exist "%%~b" (
        set "BLENDER_PATH=%%~b"
        goto FOUND_BLENDER
    )
)

REM If not found, show error
if "%BLENDER_PATH%"=="" (
    echo Blender not found in standard locations.
    echo.
    echo Please do one of the following:
    echo 1. Install Blender from https://www.blender.org/download/
    echo 2. Or run this script with the path to Blender as an argument:
    echo    run_blender.bat "C:\Path\To\Blender\blender.exe"
    echo.
    pause
    exit /b 1
)

:FOUND_BLENDER
echo Found Blender: "%BLENDER_PATH%"

REM Blender found and ready to use
echo Starting application...
echo.

REM Run Blender with our script
"%BLENDER_PATH%" --python "%~dp0blender_simple.py"

echo.
echo Application closed.
exit