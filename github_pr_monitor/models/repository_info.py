from typing import List

from github_pr_monitor.models.pull_request_info import PullRequestInfo


class RepositoryInfo:
    def __init__(self, name: str, pull_requests_info: List[PullRequestInfo]):
        self.name = name
        self.pull_requests_info = pull_requests_info
        self.status, self.is_urgent = self._get_highest_priority_status()

    def _get_highest_priority_status(self):
        priority_order = ['🔴', '💬', '🟡', '🟢', '⚪']
        default_status = priority_order[-1]
        highest_status = default_status
        is_urgent = False

        for pr in self.pull_requests_info:
            pr_status = pr.status if pr else default_status
            if pr_status in priority_order:
                is_current_higher_priority = priority_order.index(pr_status) < priority_order.index(highest_status)
                if is_current_higher_priority:
                    highest_status = pr_status
                    is_urgent = pr_status in ['🔴', '💬']
                    if pr_status == '🔴':
                        break
        return highest_status, is_urgent
