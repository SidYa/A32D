#!/bin/bash

echo "Starting 3D to 2D Animation Exporter..."
echo

# Find Blender installation
BLENDER_PATH=""

if [ -f "/usr/bin/blender" ]; then
    BLENDER_PATH="/usr/bin/blender"
elif [ -f "/usr/local/bin/blender" ]; then
    BLENDER_PATH="/usr/local/bin/blender"
elif [ -f "/opt/blender/blender" ]; then
    BLENDER_PATH="/opt/blender/blender"
elif [ -f "/snap/bin/blender" ]; then
    BLENDER_PATH="/snap/bin/blender"
elif [ -f "$HOME/blender/blender" ]; then
    BLENDER_PATH="$HOME/blender/blender"
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
