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

pip install -r requirements.txt

# Create the executable
python3 -m PyInstaller \
    --onedir \
    --strip \
    --optimize 2 \
    --noupx \
    --name rixtopic \
    rixtopic/src/main.py

# Check if the executable was created
if [ ! -f "dist/rixtopic/rixtopic" ]; then
    echo "Error: rixtopic executable not found in dist/rixtopic/"
    exit 1
fi

# Copy the required files
cp -r dist/rixtopic "$HOME/.rix/"

# Create symbolic link to rixtopic
mkdir -p "$HOME/.rix/bin/"
ln -sf "$HOME/.rix/rixtopic/rixtopic" "$HOME/.rix/bin/rixtopic"

# Create the executable
python3 -m PyInstaller \
  --onedir \
  --strip \
  --optimize 2 \
  --noupx \
  --hidden-import jsonschema \
  --hidden-import jsonmacros \
  --hidden-import open3d \
  --hidden-import collada \
  --add-data "$(python3 -c 'import collada,os; print(os.path.join(os.path.dirname(collada.__file__), "resources") + ":collada/resources")')" \
  --name jrdf \
  jrdf/src/main.py

# Check if the executable was created
if [ ! -f "dist/jrdf/jrdf" ]; then
    echo "Error: jrdf executable not found in dist/jrdf/"
    exit 1
fi

# Copy the required files
cp -r dist/jrdf "$HOME/.rix/"

# Create symbolic link to jrdf
mkdir -p "$HOME/.rix/bin/"
ln -sf "$HOME/.rix/jrdf/jrdf" "$HOME/.rix/bin/jrdf"

# Clean up
rm -rf build/ dist/

pip install -e $HOME/.rix/python/rix
deactivate
