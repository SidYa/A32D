# 3D to 2D Animation Exporter

A Blender add-on for converting 3D animations into 2D sprite sheets, perfect for 2D game development and motion graphics.

## ✨ Features

- **Import**: FBX, GLB, GLTF files with animations
- **Export**: 
  - Individual frames or sprite sheets
  - Image formats: PNG (with transparency) and WEBP
- **Camera Controls**:
  - Multiple angles: front, isometric, side
  - Adjustable camera padding
  - Automatic framing of animations
- **Animation Tools**:
  - Frame-by-frame export
  - Animation mirroring
  - Automatic grid calculation for sprite sheets

## 🚀 System Requirements

- Blender 4.0 or newer
- Python 3.x (included with Blender)
- Minimum 4GB RAM (8GB+ recommended for complex animations)
- 1GB free disk space (for temporary files)

## 📦 Installation

1. Download and install [Blender 4.0+](https://www.blender.org/download/)
2. Run the appropriate script for your OS:
   - **Windows**: Double-click `run_blender.bat`
   - **Linux**: `chmod +x run_blender_linux.sh && ./run_blender_linux.sh`
   - **MacOS**: `chmod +x run_blender_mac.sh && ./run_blender_mac.sh`

## 🎮 Usage Guide

### Basic Workflow
1. Launch the add-on using the provided script
2. In Blender, find the "Animation" panel in the 3D Viewport (right sidebar)
3. **Import** your 3D model (FBX/GLB/GLTF)
4. **Configure** export settings
5. **Export** as frames or spritesheet

### Export Settings

#### Frame Settings
- **Size**: 64x64 to 2048x2048 pixels
- **Count**: Number of frames to export
- **Format**: PNG (lossless) or WEBP (compressed)

#### Camera Settings
- **Angle**: Front, Isometric, or Side view
- **Padding**: Automatic padding around the subject (0-100%)
- **Mirroring**: Flip animation horizontally

#### Sprite Sheet Options
- **Auto Grid**: Automatically calculate optimal grid layout
- **Manual Grid**: Specify exact rows and columns

## 🔄 Supported Formats

| Type      | Formats                     |
|-----------|----------------------------|
| **Input** | FBX, GLB, GLTF             |
| **Output**| PNG (transparent), WEBP    |

## 🛠️ Troubleshooting

### Common Issues
- **No animations found**
  - Ensure your model has armature or shape key animations
  - Check that the action is not muted in the NLA Editor

- **Black background**
  - Enable "Film Transparent" in render settings
  - Check that the alpha channel is enabled in output settings

- **Model appears cut off**
  - Increase camera padding percentage
  - Adjust camera distance in the 3D view

### Performance Tips
- Lower frame count for faster previews
- Use smaller frame sizes during testing
- Close other applications to free up memory
- For large animations, export in smaller batches

## 📝 Notes
- The add-on automatically cleans up temporary files
- Original 3D scene is preserved after export
- All animations are baked into the output frames

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

Developed for game developers and digital artists.
Special thanks to the Blender community for their amazing tools and support.
