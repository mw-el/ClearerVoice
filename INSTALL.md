# ClearerVoice-Studio Installation Guide

## Quick Installation

### Prerequisites

- **Conda** (Miniconda or Anaconda)
  Download from: https://docs.conda.io/en/latest/miniconda.html
- **Git** (to clone the repository)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/modelscope/ClearerVoice-Studio.git
   cd ClearerVoice-Studio
   ```

2. **Run the installation script**
   ```bash
   ./install.sh
   ```

   The script will:
   - Create a conda environment named `clearervoice`
   - Install Python 3.8 and all dependencies
   - Install ffmpeg (required for audio processing)
   - Set up desktop integration
   - Configure environment variables

3. **Activate the environment**
   ```bash
   conda activate clearervoice
   ```

4. **Run the application**
   - **GUI Application**: Launch from your application menu or run:
     ```bash
     python clearvoice/app.py
     ```

   - **Demo Script**:
     ```bash
     cd clearvoice
     python demo.py
     ```

## Manual Installation

If you prefer manual installation or the script doesn't work:

1. **Create conda environment**
   ```bash
   conda create -n clearervoice python=3.8
   conda activate clearervoice
   ```

2. **Install ffmpeg**
   ```bash
   conda install -c conda-forge ffmpeg
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up desktop integration (optional)**
   ```bash
   # Update paths in ClearerVoice.desktop file
   # Copy to ~/.local/share/applications/
   cp ClearerVoice.desktop ~/.local/share/applications/
   update-desktop-database ~/.local/share/applications/
   ```

## System Dependencies

### Required

- **ffmpeg**: Audio/video processing (installed via conda)
- **ffmpeg binary**: System package for audio/video conversion

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# Fedora/RHEL
sudo dnf install ffmpeg

# macOS
brew install ffmpeg
```

### Optional (Recommended on Linux/GNOME)

- **zenity**: For native file picker with Nautilus integration and bookmarks

```bash
# Ubuntu/Debian
sudo apt-get install zenity

# Fedora/RHEL
sudo dnf install zenity

# If not available, app falls back to tkinter file picker
```

## Supported Python Versions

- Python 3.8 (recommended)
- Python 3.9, 3.10, 3.12 (also supported)

## Troubleshooting

### Missing C++ build tools
On Ubuntu/Debian:
```bash
sudo apt-get install build-essential
```

### pip/setuptools issues
```bash
pip install --upgrade pip setuptools wheel
```

### Desktop file not appearing
```bash
update-desktop-database ~/.local/share/applications/
```

### Model download fails
Models are downloaded automatically on first use. If download fails, check your internet connection and try again.

## Uninstallation

To remove ClearerVoice-Studio:

1. **Remove conda environment**
   ```bash
   conda deactivate
   conda env remove -n clearervoice
   ```

2. **Remove desktop integration**
   ```bash
   rm ~/.local/share/applications/ClearerVoice.desktop
   update-desktop-database ~/.local/share/applications/
   ```

3. **Remove repository**
   ```bash
   rm -rf /path/to/ClearerVoice-Studio
   ```

## Next Steps

After installation, see the [main README](README.md) for usage instructions and the [ClearVoice README](clearvoice/README.md) for detailed API documentation.

## Support

For issues or questions:
- Open an issue: https://github.com/modelscope/ClearerVoice-Studio/issues
- Email: {shengkui.zhao, zexu.pan}@alibaba-inc.com
