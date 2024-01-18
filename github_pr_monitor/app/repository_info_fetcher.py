import threading
from typing import List, Optional

from github.PullRequest import PullRequest
from github.Repository import Repository

from github_pr_monitor.app.github_api_fetcher import GithubAPIFetcher
from github_pr_monitor.models.pull_request_info import PullRequestInfo
from github_pr_monitor.models.repository_info import RepositoryInfo
from github_pr_monitor.models.reviewers_info import ReviewersInfo


class RepositoryInfoFetcher(GithubAPIFetcher):
    def __init__(self):
        super().__init__()
        self.active_threads = []
        self.abort_process = False
        self.prs_info_lock = threading.Lock()

    def set_abort_process_flag(self, value: bool) -> None:
        self.abort_process = value

    def waiting_for_stop_processing(self) -> None:
        for thread in self.active_threads:
            thread.join()

    def get_repositories_info(self, github_pat: str, repo_search_filter: Optional[str]) -> List[RepositoryInfo]:
        super().open_github_connection(github_pat)
        repositories_info: List[RepositoryInfo] = []
        try:
            repositories: List[Repository] = super().get_all_repositories(repo_search_filter)
            for repo in repositories:
                thread = threading.Thread(target=self._process_repo, args=(repo, repositories_info))
                self.active_threads.append(thread)
                thread.start()

            self.waiting_for_stop_processing()
        finally:
            self.active_threads.clear()
        return repositories_info

    def _process_repo(self, repo: Repository, repositories_info: List[RepositoryInfo]) -> None:
        repo_name = repo.name
        owner = repo.owner.login
        prs = super().get_pull_requests_for_repo(owner, repo_name)
        pull_requests_info: List[PullRequestInfo] = [self._format_pr_info(owner, pr) for pr in prs]
        with self.prs_info_lock:
            repositories_info.append(RepositoryInfo(name=repo_name, pull_requests_info=pull_requests_info))

    def _format_pr_info(self, owner: str, pr: PullRequest) -> Optional[PullRequestInfo]:
        if self.abort_process:
            return None
        reviewers_info: ReviewersInfo = super().get_reviewers_info(owner=owner,
                                                                   repo=pr.head.repo.name,
                                                                   id=pr.number,
                                                                   base_branch=pr.base.ref)
        return PullRequestInfo(title=pr.title,
                               url=pr.html_url,
                               id=pr.number,
                               is_draft=pr.draft,
                               reviewers_info=reviewers_info)