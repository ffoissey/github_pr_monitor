import logging
from time import time
from typing import List, Optional

from github import Github, GithubException
from github.Auth import Token
from github.Branch import Branch
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestReview import PullRequestReview
from github.Repository import Repository
from github.RequiredPullRequestReviews import RequiredPullRequestReviews

from github_pr_monitor.config import APPLICATION_MAX_THREADS
from github_pr_monitor.models.reviewers_info import ReviewersInfo


class GithubAPIFetcher:
    _DEFAULT_POOL_SIZE: int = APPLICATION_MAX_THREADS
    _CACHE_EXPIRY: int = 3600
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GithubAPIFetcher, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.github: Optional[Github] = None
            self.github_pat = None
            self.pool_size = self._DEFAULT_POOL_SIZE
            self.initialized = True
            self.cache = {}
            self.cache_expiry = self._CACHE_EXPIRY

    def __del__(self):
        self.github.close()

    def open_github_connection(self, github_pat: str) -> None:
        if github_pat != self.github_pat:
            if self.github is not None:
                self._close_github_connection()
            self.github_pat = github_pat
            auth = Token(github_pat)
            self.github = Github(auth=auth, pool_size=self.pool_size, per_page=100)

    def get_all_repositories(self, filter_keyword: str = None) -> List[Repository]:
        cache_key = f"repos_{filter_keyword or 'all'}"
        cached_repos = self._get_from_repositories_cache(cache_key)

        if cached_repos is not None:
            return cached_repos

        repos = []
        for repo in self.github.get_user().get_repos():
            if not filter_keyword or (filter_keyword.lower() in repo.name.lower()):
                repos.append(repo)

        self._add_to_repositories_cache(cache_key, repos)
        return repos

    def get_current_user_login(self) -> str:
        return self.github.get_user().login

    @staticmethod
    def get_reviewers_info(pull_request: PullRequest, current_user: str) -> Optional[ReviewersInfo]:
        try:
            branch_required_reviews: RequiredPullRequestReviews = GithubAPIFetcher.get_branch_requested_reviewers(
                pull_request)
            reviews: PaginatedList[PullRequestReview] = pull_request.get_reviews()

            return ReviewersInfo(pull_request=pull_request, reviews=reviews,
                                 branch_required_reviews=branch_required_reviews, current_user=current_user)
        except GithubException as e:
            logging.warning(f'Failed to fetch PR reviewers information for repository {pull_request.head.repo}: {e}')
            return None

    @staticmethod
    def get_branch_requested_reviewers(pull_request: PullRequest) -> Optional[RequiredPullRequestReviews]:
        branch_name: str = pull_request.base.ref
        try:
            branch: Branch = pull_request.head.repo.get_branch(branch_name)
            return branch.get_required_pull_request_reviews()
        except GithubException as e:
            logging.info(f'Failed to fetch branch protection information for repo "{pull_request.head.repo}" on branch "{branch_name}": {e}')
            return None

    @staticmethod
    def get_pull_requests_for_repo(repository: Repository) -> PaginatedList[PullRequest]:
        return repository.get_pulls(state='open')

    def _close_github_connection(self) -> None:
        if self.github is not None:
            self.github.close()
            self.github = None

    def _get_from_repositories_cache(self, key) -> Optional[List[Repository]]:
        cached_data = self.cache.get(key)
        if cached_data:
            data, timestamp = cached_data
            if time() - timestamp < self.cache_expiry:
                return data
            else:
                logging.info(f'Remove key "{key}" from repositories cache')
        return None

    def _add_to_repositories_cache(self, key, data) -> None:
        self.cache[key] = (data, time())
        logging.info(f'Add key "{key}" to repositories cache')
