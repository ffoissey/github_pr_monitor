#!/bin/bash

set -e
echo "Script will exit immediately if any command exits with a non-zero status."

VENV_NAME="pyinstallerenv"
APP_NAME="github_pr_monitor"
APP_PATH="dist/${APP_NAME}.app"
REQUIREMENTS_PATH="github_pr_monitor/requirement.txt"
PYINSTALLER_SPEC_FILE="github_pr_monitor.spec"

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it before continuing." >&2
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo "pip is not installed. Please install it before continuing." >&2
    exit 1
fi

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
pip install -r ${REQUIREMENTS_PATH}

echo "Building the application with PyInstaller..."
pyinstaller ${PYINSTALLER_SPEC_FILE}

if [ ! -d "${APP_PATH}" ]; then
    echo "Application build failed. Please check the output for errors." >&2
    exit 1
fi

read -p "Do you want to add the application to startup items? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Adding the application to startup items..."
    osascript -e "tell application \"System Events\" to make new login item at end with properties {path:\"${PWD}/${APP_PATH}\", hidden:false}"
    echo "Application added to startup items."
fi

echo
read -p "Do you want to launch the application now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Launching the application..."
    open ${APP_PATH}
else
    echo "You can launch the application later by running 'open ${APP_PATH}'."
fi

echo "Setup process completed."
