#!/bin/bash

echo "Starting 3D to 2D Animation Exporter..."
echo

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
    echo "Please install Blender or specify path manually."
    echo
    echo "Download Blender: https://www.blender.org/download/"
    read -p "Press any key to continue..."
    exit 1
fi

echo "Found Blender: $BLENDER_PATH"
echo "Starting application..."
echo

# Run Blender with our script
"$BLENDER_PATH" --python blender_simple.py

read -p "Press any key to continue..."