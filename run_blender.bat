@echo off
chcp 65001 >nul
echo Starting 3D to 2D Animation Exporter...
echo.

REM Find Blender installation
set "BLENDER_PATH="

if exist "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" (
    set "BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
) else if exist "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe" (
    set "BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"
) else if exist "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe" (
    set "BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
) else if exist "C:\Program Files\Blender Foundation\Blender 3.5\blender.exe" (
    set "BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 3.5\blender.exe"
)

if "%BLENDER_PATH%"=="" (
    echo Blender not found in standard locations.
    echo Please install Blender or specify path manually.
    echo.
    echo Download Blender: https://www.blender.org/download/
    pause
    exit /b 1
)

echo Found Blender: "%BLENDER_PATH%"
echo Starting application...
echo.

REM Run Blender with our script
"%BLENDER_PATH%" --python blender_simple.py

pause