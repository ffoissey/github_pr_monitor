#!/bin/bash

REQUIREMENTS_PATH="github_pr_monitor/requirement.txt"
PYINSTALLER_SPEC_FILE="github_pr_monitor.spec"
UNINSTALL_SCRIPT="./uninstall.sh"

source .common_vars.sh

if [ -d "${VENV_NAME}" ] || [ -d "${PYINSTALLER_BUILD_DIR}" ] || [ -d "${PYINSTALLER_DIST_DIR}" ]; then
    echo -e "${YELLOW}Previous installation detected. Uninstalling...${NC}"
    bash ${UNINSTALL_SCRIPT}
fi

echo
echo -e "${GREY}####### Beginning the installation process #######${NC}"
echo

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}python3 is not installed. Please install it before continuing.${NC}" >&3
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}pip3 is not installed. Please install it before continuing.${NC}" >&2
    exit 1
fi

if [ ! -d "${VENV_NAME}" ]; then
    echo -e "${GREY}Creating virtual environment...${NC}"
    python3 -m venv "${VENV_NAME}"
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}" >&2
fi

echo -e "${GREY}Activating virtual environment...${NC}"
source "${VENV_NAME}"/bin/activate

echo -e "${GREY}Installing dependencies...${NC}"
pip3 install --upgrade pip
pip3 install -r ${REQUIREMENTS_PATH}

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
    if osascript -e "tell application \"System Events\" to get the name of every login item" | grep -q "${APP_OUTPUT_NAME}"; then
        echo -e "${YELLOW}Application already added to startup items.${NC}"
    else
        if osascript -e "tell application \"System Events\" to make new login item at end with properties {path:\"${PWD}/${APP_PATH}\", hidden:false, name:\"${APP_NAME}\"}"; then
            echo -e "${GREEN}Application added to startup items.${NC}"
        else
            echo -e "${RED}Failed to add the application to startup items.${NC}"
        fi
    fi
fi

echo
echo -en "${BLUE}Do you want to launch the application now? (y/n) ${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREY}Launching the application...${NC}"
    open "${APP_PATH}"
else
    echo -e "${PURPLE}You can launch the application later by running 'open ${APP_PATH}'.${NC}"
fi

echo -e "${GREEN}Setup process completed.${NC}"
echo
