from typing import List, Tuple

from github_pr_monitor.constants.app_setting_constants import PR_REPO_STATUS_MAPPING, PR_PRIORITY_ORDER
from github_pr_monitor.constants.emojis import PR_URGENT_EMOJI, PR_COMMENT_EMOJI
from github_pr_monitor.models.pull_request_info import PullRequestInfo


class RepositoryInfo:
    def __init__(self, name: str, pull_requests_info: List[PullRequestInfo]):
        self.name = name
        self.pull_requests_info = pull_requests_info
        self.status, self.is_urgent = self._get_highest_priority_status()

    def format_repo_title(self) -> str:
        return f"{self.status} {self.name}"

    def _get_highest_priority_status(self) -> Tuple[str, bool]:
        current_priority = PR_PRIORITY_ORDER[-1]
        is_urgent = False
        for pr in self.pull_requests_info:
            if PR_PRIORITY_ORDER.index(pr.status) < PR_PRIORITY_ORDER.index(current_priority):
                current_priority = pr.status
                is_urgent = pr.status in [PR_URGENT_EMOJI, PR_COMMENT_EMOJI]
        return PR_REPO_STATUS_MAPPING[current_priority], is_urgent
