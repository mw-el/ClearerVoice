#!/bin/bash

# ClearerVoice Installation Script
# This script installs ClearerVoice-Studio and sets up desktop integration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the absolute path of the installation directory
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="clearervoice"

echo -e "${GREEN}ClearerVoice-Studio Installation${NC}"
echo "=================================="
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda is not installed${NC}"
    echo "Please install Miniconda or Anaconda first:"
    echo "https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found conda"

# Check if environment already exists
if conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "${YELLOW}Warning: Environment '${ENV_NAME}' already exists${NC}"
    read -p "Do you want to remove it and reinstall? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing environment..."
        conda env remove -n ${ENV_NAME} -y
    else
        echo "Installation cancelled."
        exit 0
    fi
fi

# Create conda environment
echo ""
echo "Creating conda environment '${ENV_NAME}' with Python 3.8..."
conda create -n ${ENV_NAME} python=3.8 -y

echo -e "${GREEN}✓${NC} Environment created"

# Activate environment
echo ""
echo "Installing dependencies..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate ${ENV_NAME}

# Install ffmpeg if not available
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing ffmpeg via conda..."
    conda install -c conda-forge ffmpeg -y
    echo -e "${GREEN}✓${NC} ffmpeg installed"
else
    echo -e "${GREEN}✓${NC} ffmpeg already installed"
fi

# Install Python dependencies
pip install -r "${INSTALL_DIR}/requirements.txt"
echo -e "${GREEN}✓${NC} Python dependencies installed"

# Set environment variables for the conda environment
CONDA_ENV_DIR="$(conda info --base)/envs/${ENV_NAME}"
mkdir -p "${CONDA_ENV_DIR}/etc/conda/activate.d"
mkdir -p "${CONDA_ENV_DIR}/etc/conda/deactivate.d"

# Create activation script to set environment variables
cat > "${CONDA_ENV_DIR}/etc/conda/activate.d/env_vars.sh" << EOF
#!/bin/bash
export CLEARVOICE_HOME="${INSTALL_DIR}"
export PATH="\${PATH}:${INSTALL_DIR}"
EOF

# Create deactivation script to unset environment variables
cat > "${CONDA_ENV_DIR}/etc/conda/deactivate.d/env_vars.sh" << EOF
#!/bin/bash
unset CLEARVOICE_HOME
EOF

echo -e "${GREEN}✓${NC} Environment variables configured"

# Set up desktop integration
echo ""
echo "Setting up desktop integration..."

# Get the Python path for the environment
PYTHON_PATH="${CONDA_ENV_DIR}/bin/python"

# Create desktop file with correct paths
DESKTOP_FILE="${INSTALL_DIR}/ClearerVoice.desktop"
cat > "${DESKTOP_FILE}" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ClearerVoice
GenericName=Speech Enhancement
Comment=AI-powered speech enhancement and processing
Exec=${PYTHON_PATH} ${INSTALL_DIR}/clearvoice/app.py
Path=${INSTALL_DIR}
Icon=${INSTALL_DIR}/clearervoice.png
Terminal=false
Categories=Audio;AudioVideo;
StartupNotify=true
StartupWMClass=clearervoice
EOF

chmod +x "${DESKTOP_FILE}"

# Validate desktop file
if command -v desktop-file-validate &> /dev/null; then
    desktop-file-validate "${DESKTOP_FILE}" || echo -e "${YELLOW}Warning: Desktop file validation had warnings${NC}"
fi

# Install desktop file
DESKTOP_DIR="${HOME}/.local/share/applications"
mkdir -p "${DESKTOP_DIR}"
cp "${DESKTOP_FILE}" "${DESKTOP_DIR}/"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "${DESKTOP_DIR}"
fi

echo -e "${GREEN}✓${NC} Desktop integration installed"

# Download models on first run (optional)
echo ""
read -p "Do you want to download the default model now? This may take a few minutes. (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Pre-downloading MossFormer2_SE_48K model..."
    cd "${INSTALL_DIR}/clearvoice"
    python -c "from clearvoice import ClearVoice; ClearVoice(task='speech_enhancement', model_names=['MossFormer2_SE_48K'])" || echo -e "${YELLOW}Model download will happen on first use${NC}"
fi

echo ""
echo -e "${GREEN}=================================="
echo "Installation Complete!"
echo "==================================${NC}"
echo ""
echo "To use ClearerVoice:"
echo "  1. Activate the environment: conda activate ${ENV_NAME}"
echo "  2. Run the GUI app from your application menu or:"
echo "     python ${INSTALL_DIR}/clearvoice/app.py"
echo "  3. Or run the demo: cd clearvoice && python demo.py"
echo ""
echo "The application has been added to your desktop menu."
echo ""
