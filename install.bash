#!/bin/bash

set -e

mkdir -p $HOME/.rix/python/

cp -r rix $HOME/.rix/python/

# Check if python3.12 is available
if ! command -v python3.12 &>/dev/null; then
    echo "Error: python3.12 is not installed or not in PATH."
    echo "Please install Python 3.12 and try again."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment in $HOME/.rix/venv/"
python3.12 -m venv $HOME/.rix/venv/

# Verify success
if [ $? -eq 0 ]; then
    echo "Virtual environment created successfully."
    echo "To activate it: source $HOME/.rix/bin/activate"
else
    echo "Failed to create virtual environment."
    exit 2
fi

echo "Installing rix-py"
source $HOME/.rix/venv/bin/activate

# Copy rixinfo
cp -r rixinfo $HOME/.rix/

# Ensure main.py is executable
chmod +x "$HOME/.rix/rixinfo/src/main.py"

# Create symbolic link to rixinfo
mkdir -p "$HOME/.rix/bin/"
ln -sf "$HOME/.rix/rixinfo/src/main.py" "$HOME/.rix/bin/rixinfo"

pip install -e $HOME/.rix/python/rix
deactivate
