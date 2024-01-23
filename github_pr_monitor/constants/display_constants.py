from github_pr_monitor.constants.emojis import QUITTING_EMOJI, IN_PROGRESS_EMOJI

APP_NAME: str = "PR Monitor"
APP_QUITTING: str = f"{APP_NAME} {QUITTING_EMOJI} (Quitting)"

DEFAULT_ERROR: str = "Unexpected Error"
INVALID_PAT_MSG: str = "(Invalid PAT)"
NETWORK_ERROR_MSG: str = "(Network Error)"

REFRESH_MENU: str = "Force Refresh"
REFRESHING: str = f"Refreshing… {IN_PROGRESS_EMOJI}"
SETTINGS_MENU: str = "Settings"
QUIT_MENU: str = "Quit"
QUITTING: str = f"Quitting… {IN_PROGRESS_EMOJI}"

PAT_SETTING_MENU: str = "Github Personal Access Token"
REPOSITORY_FILTER_SETTING_MENU: str = "Repository Search Filter"
REFRESH_DELAY_SETTING_MENU: str = "Refresh Delay"



