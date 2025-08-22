# 3D to 2D Animation Exporter

A Blender add-on for converting 3D animations into 2D sprite sheets for game development.

## Features

- **Import**: FBX, GLB, GLTF files with animations
- **Export**: Individual frames or sprite sheets (PNG/WEBP)
- **Camera**: Front, Isometric, Side, Custom angles with flip option

## Installation

1. Install [Blender 4.0+](https://www.blender.org/download/)
2. Windows: Double-click `run_blender.bat`
3. macOS / Linux: in a terminal run `chmod +x run_blender_*.sh` (if needed) then `./run_blender_mac.sh` or `./run_blender_linux.sh`

## Usage

1. Launch via `run_blender.bat` or `./run_blender_mac.sh`, `./run_blender_linux.sh`.
2. Find "A32D" panel in 3D Viewport sidebar (opened automatically)
3. Import your 3D model (FBX/GLB/GLTF)
4. Configure settings and export

## Settings

- **Frame Size**: 64x64 to 2048x2048 pixels
- **Frame Range**: Start/End frame selection
- **Camera Angle**: Front, Isometric, Side, or Custom
- **Flip Camera**: Mirror animation horizontally
- **Padding**: Add space around model (optional)
- **Format**: PNG or WEBP output

## Supported Formats

- **Input**: FBX, GLB, GLTF
- **Output**: PNG, WEBP
