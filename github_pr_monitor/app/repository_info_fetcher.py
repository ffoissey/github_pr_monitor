import threading
from typing import List, Optional

from github.PullRequest import PullRequest
from github.Repository import Repository

from github_pr_monitor.app.github_api_fetcher import GithubAPIFetcher
from github_pr_monitor.config import THREAD_MANAGER
from github_pr_monitor.models.pull_request_info import PullRequestInfo
from github_pr_monitor.models.repository_info import RepositoryInfo
from github_pr_monitor.models.reviewers_info import ReviewersInfo


class RepositoryInfoFetcher(GithubAPIFetcher):
    def __init__(self):
        super().__init__()
        self.abort_process = False
        self.prs_info_lock = threading.Lock()
        self.thread_manager = THREAD_MANAGER

    def set_abort_process_flag(self, value: bool) -> None:
        self.abort_process = value

    def get_repositories_info(self, github_pat: str, repo_search_filter: Optional[str]) -> List[RepositoryInfo]:
        super().open_github_connection(github_pat)
        repositories_info: List[RepositoryInfo] = []
        try:
            repositories: List[Repository] = super().get_all_repositories(repo_search_filter)
            for repo in repositories:
                self.thread_manager.start_thread(self._process_repo, args=(repo, repositories_info))
        finally:
            self.thread_manager.wait_for_all_threads()
        return sorted(repositories_info, key=lambda repository_info: repository_info.name)

    def _process_repo(self, repo: Repository, repositories_info: List[RepositoryInfo]) -> None:
        if self.abort_process is True:
            return None
        prs = super().get_pull_requests_for_repo(repo)
        pull_requests_info: List[PullRequestInfo] = list(filter(lambda pr: pr is not None,
                                                                [self._format_pr_info(pr) for pr in prs]))
        pull_requests_info = sorted(pull_requests_info, key=lambda pull_request_info: pull_request_info.id)
        with self.prs_info_lock:
            repositories_info.append(RepositoryInfo(name=repo.name, url=repo.html_url, pull_requests_info=pull_requests_info))

    def _format_pr_info(self, pr: PullRequest) -> Optional[PullRequestInfo]:
        if self.abort_process is True:
            return None
        current_user: str = super().get_current_user_login()
        is_author: bool = pr.user.login == current_user
        reviewers_info: ReviewersInfo = super().get_reviewers_info(pull_request=pr, current_user=current_user)
        return PullRequestInfo(title=pr.title,
                               url=pr.html_url,
                               id=pr.number,
                               is_draft=pr.draft,
                               is_author=is_author,
                               reviewers_info=reviewers_info)

