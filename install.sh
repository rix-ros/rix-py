#!/bin/bash

cp -r rixcore ~/.rix/python/

# Check if python3.12 is available
if ! command -v python3.12 &>/dev/null; then
    echo "Error: python3.12 is not installed or not in PATH."
    echo "Please install Python 3.12 and try again."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment in ~/.rix/venv/"
python3.12 -m venv ~/.rix/venv/

# Verify success
if [ $? -eq 0 ]; then
    echo "Virtual environment created successfully."
    echo "To activate it: source ~/.rix/bin/activate"
else
    echo "Failed to create virtual environment."
    exit 2
fi

echo "Installing rix-py"
source ~/.rix/venv/bin/activate
pip install -e ~/.rix/python/rixmsg
pip install ~/.rix/python/rixcore
deactivate
