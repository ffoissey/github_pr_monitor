from typing import List

from github_pr_monitor.models.pull_request_info import PullRequestInfo


class RepositoryInfo:
    def __init__(self, name: str, pull_requests_info: List[PullRequestInfo]):
        self.name = name
        self.pull_requests_info = pull_requests_info
        self.status, self.is_urgent = self._get_highest_priority_status()

    def _get_highest_priority_status(self):
        pr_repo_status_mapping = {
            '🔴': '🔴',
            '💬': '🟠',
            '🟡': '🟡',
            '✅': '🟢',
            '📃': '⚪'
        }
        priority_order = ['🔴', '💬', '🟡', '✅', '📃']
        current_priority = priority_order[-1]
        mandatory = ''
        is_urgent = False
        for pr in self.pull_requests_info:
            if priority_order.index(pr.status) < priority_order.index(current_priority):
                current_priority = pr.status
                is_urgent = pr.status in ['🔴', '💬']
                if pr.reviewers_info.is_mandatory:
                    mandatory = '❗️'
        return mandatory + pr_repo_status_mapping[current_priority], is_urgent
