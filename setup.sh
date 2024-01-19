#!/bin/bash

set -e

VENV_NAME="pyinstallerenv"

if [ ! -d "${VENV_NAME}" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ${VENV_NAME}
else
    echo "Virtual environment already exists." >&2
fi

echo "Activating virtual environment..."
source ${VENV_NAME}/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r github_pr_monitor/requirement.txt

echo "Building the application with PyInstaller..."
pyinstaller github_pr_monitor.spec

echo "Setup process completed."