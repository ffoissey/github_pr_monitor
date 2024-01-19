#!/bin/bash

VENV_NAME="pyinstallerenv"
APP_NAME="github_pr_monitor"
APP_PATH="dist/${APP_NAME}.app"
REQUIREMENTS_PATH="github_pr_monitor/requirement.txt"
PYINSTALLER_SPEC_FILE="github_pr_monitor.spec"

# Colors
RED="\033[31;1m"
GREEN="\033[32;1m"
YELLOW="\033[33;1m"
BLUE="\033[34;1m"
PURPLE="\033[35;1m"
GREY="\033[37;1m"
NC="\033[0;1m"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install it before continuing.${NC}" >&2
    exit 1
fi

if ! command -v pip &> /dev/null; then
    echo -e "${RED}pip is not installed. Please install it before continuing.${NC}" >&2
    exit 1
fi

if [ ! -d "${VENV_NAME}" ]; then
    echo -e "${GREY}Creating virtual environment...${NC}"
    python3 -m venv ${VENV_NAME}
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}" >&2
fi

echo -e "${GREY}Activating virtual environment...${NC}"
source ${VENV_NAME}/bin/activate

echo -e "${GREY}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r ${REQUIREMENTS_PATH}

echo -e "${GREY}Building the application with PyInstaller...${NC}"
pyinstaller ${PYINSTALLER_SPEC_FILE}

if [ ! -d "${APP_PATH}" ]; then
    echo -e "${RED}Application build failed. Please check the output for errors.${NC}" >&2
    exit 1
fi

echo -en "${BLUE}Do you want to add the application to startup items? (y/n) ${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREY}Adding the application to startup items...${NC}"
    osascript -e "tell application \"System Events\" to make new login item at end with properties {path:\"${PWD}/${APP_PATH}\", hidden:false, name:\"PR Monitor\"}"
    echo -e "${GREEN}Application added to startup items.${NC}"
fi

echo
echo -en "${BLUE}Do you want to launch the application now? (y/n) ${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREY}Launching the application...${NC}"
    open ${APP_PATH}
else
    echo -e "${PURPLE}You can launch the application later by running 'open ${APP_PATH}'.${NC}"
fi

echo -e "${GREEN}Setup process completed.${NC}"
