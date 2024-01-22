#!/bin/bash

source .common_vars.sh

echo
echo -e "${GREY}####### Beginning the uninstallation process #######${NC}"
echo

echo -e "${GREY}Checking and removing the application from startup items, if present...${NC}"
if osascript -e "tell application \"System Events\" to get the name of every login item" | grep -q "${APP_OUTPUT_NAME}"; then
    if osascript -e "tell application \"System Events\" to delete login item \"${APP_OUTPUT_NAME}\""; then
        echo -e "${GREEN}Application removed from startup items.${NC}"
    else
        echo -e "${RED}Failed to remove the application from startup items.${NC}"
    fi
else
    echo -e "${YELLOW}Application not found in startup items. No need to remove.${NC}"
fi

echo -e "${GREEN}Removing the virtual environment, application and build files...${NC}"
rm -Rf "${VENV_NAME}"
rm -Rf "${PYINSTALLER_BUILD_DIR}"
rm -Rf "${PYINSTALLER_DIST_DIR}"

echo -e "${GREEN}Uninstallation completed.${NC}"
echo
