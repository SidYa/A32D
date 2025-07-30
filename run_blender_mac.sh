#!/bin/bash

echo "Starting 3D to 2D Animation Exporter..."
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/blender_simple.py"

# Find Blender installation on macOS
BLENDER_PATH=""

if [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
elif [ -f "/usr/local/bin/blender" ]; then
    BLENDER_PATH="/usr/local/bin/blender"
elif [ -f "$HOME/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER_PATH="$HOME/Applications/Blender.app/Contents/MacOS/Blender"
fi

if [ -z "$BLENDER_PATH" ]; then
    echo "Blender not found in standard locations."
    echo "Please install Blender 4.0+ from: https://www.blender.org/download/"
    exit 1
fi

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: blender_simple.py not found in $SCRIPT_DIR"
    exit 1
fi

echo "Found Blender: $BLENDER_PATH"
echo "Starting with addon..."
echo

# Run Blender with our addon script
"$BLENDER_PATH" --python "$PYTHON_SCRIPT"