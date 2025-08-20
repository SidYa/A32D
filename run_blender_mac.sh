#!/bin/bash

echo "Starting 3D to 2D Animation Exporter..."
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/blender_simple.py"

# Function to find Blender on macOS
find_blender() {
    # Check common installation paths
    local paths=(
        "/Applications/Blender.app/Contents/MacOS/Blender"
        "$HOME/Applications/Blender.app/Contents/MacOS/Blender"
        "/Applications/Blender-*.app/Contents/MacOS/Blender"
        "$HOME/Applications/Blender-*.app/Contents/MacOS/Blender"
        "/usr/local/bin/blender"
        "/opt/homebrew/bin/blender"
        "$HOME/Homebrew/bin/blender"
        "/opt/X11/bin/blender"
    )
    
    # Check if which command is available
    if command -v blender &> /dev/null; then
        BLENDER_PATH=$(command -v blender)
        echo "Found Blender using 'which': $BLENDER_PATH"
        return 0
    fi
    
    # Check common paths
    for path in "${paths[@]}"; do
        # Expand glob patterns
        for expanded_path in $path; do
            if [ -f "$expanded_path" ] && [ -x "$expanded_path" ]; then
                BLENDER_PATH="$expanded_path"
                echo "Found Blender at: $BLENDER_PATH"
                return 0
            fi
        done
    done
    
    # Try to find using mdfind (Spotlight)
    echo "Searching for Blender using Spotlight (this might take a moment)..."
    local found_path=$(mdfind "kMDItemCFBundleIdentifier == 'org.blenderfoundation.blender'" | head -n 1)
    
    if [ -n "$found_path" ]; then
        BLENDER_PATH="$found_path/Contents/MacOS/Blender"
        if [ -f "$BLENDER_PATH" ] && [ -x "$BLENDER_PATH" ]; then
            echo "Found Blender using Spotlight: $BLENDER_PATH"
            return 0
        fi
    fi
    
    return 1
}

# Check if path was provided as argument
if [ $# -gt 0 ]; then
    if [ -f "$1" ] && [ -x "$1" ]; then
        BLENDER_PATH="$1"
        echo "Using provided Blender path: $BLENDER_PATH"
    else
        echo "Error: Provided Blender path does not exist or is not executable: $1"
        exit 1
    fi
else
    # Try to find Blender automatically
    if ! find_blender; then
        echo "Blender not found in standard locations."
        echo "Please do one of the following:"
        echo "1. Install Blender from https://www.blender.org/download/"
        echo "2. Run this script with the path to Blender as an argument:"
        echo "   ./run_blender_mac.sh /path/to/Blender.app/Contents/MacOS/Blender"
        echo "3. Make sure Blender is in your PATH"
        exit 1
    fi
fi

# Verify Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: blender_simple.py not found in $SCRIPT_DIR"
    exit 1
fi

# Get Blender version
BLENDER_VERSION=$("$BLENDER_PATH" --version 2>/dev/null | head -n 1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)

echo "Blender version: ${BLENDER_VERSION:-unknown}"
echo "Starting application..."
echo

# Run Blender with our script
"$BLENDER_PATH" --python "$PYTHON_SCRIPT"

echo -e "\nApplication closed."