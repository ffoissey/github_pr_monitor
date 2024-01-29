from typing import Dict, List

from github_pr_monitor.constants.emojis import PR_URGENT_EMOJI, PR_COMMENT_EMOJI, PR_OK_EMOJI, PR_DRAFT_EMOJI, \
    PR_IMPORTANT_EMOJI, REPO_WITH_PR_URGENT_EMOJI, REPO_WITH_PR_COMMENT_EMOJI, REPO_WITH_PR_OK_EMOJI, \
    REPO_WITH_PR_DRAFT_EMOJI, REPO_WITH_PR_IMPORTANT_EMOJI

DIALOG_HEIGHT: int = 25
DIALOG_WIDTH: int = 500

DEFAULT_REFRESH_DELAY: int = 300
UPDATE_CHECKER_DELAY: int = 1

DEFAULT_NOTIFICATION_DELAY: int = 3600
DEFAULT_CONFIG_DIR: str = '~/Library/Application Support/PRMonitor'
DEFAULT_CONFIG_FILE_NAME: str = 'config.json'
REPO_SEARCH_FILTER_CONFIG_KEY: str = 'repo_search_filter'
REFRESH_TIME_CONFIG_KEY: str = 'refresh_time'

PR_REPO_STATUS_MAPPING: Dict[str, str] = {
    PR_URGENT_EMOJI: REPO_WITH_PR_URGENT_EMOJI,
    PR_COMMENT_EMOJI: REPO_WITH_PR_COMMENT_EMOJI,
    PR_IMPORTANT_EMOJI: REPO_WITH_PR_IMPORTANT_EMOJI,
    PR_OK_EMOJI: REPO_WITH_PR_OK_EMOJI,
    PR_DRAFT_EMOJI: REPO_WITH_PR_DRAFT_EMOJI
}
PR_PRIORITY_ORDER: List[str] = [PR_URGENT_EMOJI, PR_COMMENT_EMOJI, PR_IMPORTANT_EMOJI, PR_OK_EMOJI, PR_DRAFT_EMOJI]
