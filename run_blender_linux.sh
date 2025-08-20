#!/bin/bash

echo "Starting 3D to 2D Animation Exporter..."
echo

# Function to find Blender in common locations
find_blender() {
    # Check common installation paths
    local paths=(
        "/usr/bin/blender"
        "/usr/local/bin/blender"
        "/snap/bin/blender"
        "$HOME/blender/blender"
        "$HOME/.local/bin/blender"
        "/opt/blender/blender"
        "/opt/blender-*/blender"
        "/usr/lib/blender-*/blender"
        "$HOME/Applications/blender/blender"
        "$HOME/.steam/steam/steamapps/common/Blender/blender"
    )
    
    # Check if which command is available
    if command -v blender &> /dev/null; then
        BLENDER_PATH=$(command -v blender)
        echo "Found Blender using 'which': $BLENDER_PATH"
        return 0
    fi
    
    # Check common paths
    for path in "${paths[@]}"; do
        if [ -f "$path" ]; then
            BLENDER_PATH=$(realpath "$path")
            echo "Found Blender at: $BLENDER_PATH"
            return 0
        fi
    done
    
    # Try to find using find command (might be slow)
    echo "Searching for Blender in common directories (this might take a moment)..."
    local found_path=$(find /usr /opt "$HOME" -type f -name "blender" -executable -print -quit 2>/dev/null)
    
    if [ -n "$found_path" ]; then
        BLENDER_PATH=$(realpath "$found_path")
        echo "Found Blender at: $BLENDER_PATH"
        return 0
    fi
    
    return 1
}

# Check if path was provided as argument
if [ $# -gt 0 ]; then
    if [ -f "$1" ]; then
        BLENDER_PATH="$1"
        echo "Using provided Blender path: $BLENDER_PATH"
    else
        echo "Error: Provided Blender path does not exist: $1"
        exit 1
    fi
else
    # Try to find Blender automatically
    if ! find_blender; then
        echo "Blender not found in standard locations."
        echo "Please do one of the following:"
        echo "1. Install Blender from https://www.blender.org/download/"
        echo "2. Run this script with the path to Blender as an argument:"
        echo "   ./run_blender_linux.sh /path/to/blender"
        echo "3. Make sure Blender is in your PATH"
        read -p "Press any key to exit..."
        exit 1
    fi
fi

# Get Blender version
BLENDER_VERSION=$("$BLENDER_PATH" --version 2>/dev/null | head -n 1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1)

echo "Blender version: ${BLENDER_VERSION:-unknown}"
echo "Starting application..."
echo

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Run Blender with our script
"$BLENDER_PATH" --python "$SCRIPT_DIR/blender_simple.py"

echo "\nApplication closed."
