#!/bin/bash
# Startup script for ClearerVoice application
# Follows best practices from DICTATE docs/DESKTOP_INTEGRATION.md

echo "🚀 Starting ClearerVoice..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find conda installation
if [ -f "$HOME/miniconda3/bin/activate" ]; then
    CONDA_BASE="$HOME/miniconda3"
elif [ -f "$HOME/anaconda3/bin/activate" ]; then
    CONDA_BASE="$HOME/anaconda3"
else
    echo "❌ Error: Cannot find conda installation in $HOME/miniconda3 or $HOME/anaconda3"
    exit 1
fi

# Activate conda base
source "$CONDA_BASE/bin/activate"

# Activate specific environment
conda activate clearervoice

# Verify activation
if [ "$CONDA_DEFAULT_ENV" != "clearervoice" ]; then
    echo "❌ Error: clearervoice environment could not be activated"
    exit 1
fi

echo "✅ Environment clearervoice activated"

# Set CUDA library path for GPU support
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Add cuDNN library path from conda environment (dynamic Python version detection)
PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
CUDNN_LIB_PATH="$CONDA_BASE/envs/clearervoice/lib/python${PYTHON_VERSION}/site-packages/nvidia/cudnn/lib"
if [ -d "$CUDNN_LIB_PATH" ]; then
    export LD_LIBRARY_PATH="$CUDNN_LIB_PATH:$LD_LIBRARY_PATH"
    echo "✓ Added cuDNN library path: $CUDNN_LIB_PATH"
fi

# Change to clearvoice subdirectory (critical for ClearerVoice imports)
cd "$SCRIPT_DIR/clearvoice"

# Start the app with explicit conda Python path (critical for desktop integration)
echo "🎯 Starting ClearerVoice app..."
"$CONDA_BASE/envs/clearervoice/bin/python" app.py

echo "👋 ClearerVoice closed"
