import logging
from typing import List, Optional

from github import Github, GithubException
from github.Auth import Token
from github.Branch import Branch
from github.BranchProtection import BranchProtection
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestReview import PullRequestReview
from github.Repository import Repository
from github.RequiredPullRequestReviews import RequiredPullRequestReviews

from github_pr_monitor.models.reviewers_info import ReviewersInfo


class GithubAPIFetcher:

    _DEFAULT_POOL_SIZE = 20
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

    def __del__(self):
        self.github.close()

    def open_github_connection(self, github_pat: str) -> None:
        if github_pat != self.github_pat:
            if self.github is not None:
                self._close_github_connection()
            self.github_pat = github_pat
            auth = Token(github_pat)
            self.github = Github(auth=auth, pool_size=self.pool_size, per_page=100)

    def _close_github_connection(self) -> None:
        if self.github is not None:
            self.github.close()
            self.github = None

    def get_all_repositories(self, filter_keyword: str = None) -> List[Repository]:
        filter_keyword = filter_keyword.lower() if filter_keyword else None
        repos = []
        for repo in self.github.get_user().get_repos(sort='full_name'):
            if not filter_keyword or (filter_keyword in repo.name.lower()):
                repos.append(repo)
        self._adjust_connection_pool_size(len(repos))
        return repos

    def get_current_user_login(self) -> str:
        return self.github.get_user().login

    def get_branch_requested_reviewers(self, pull_request: PullRequest):
        branch_name: str = pull_request.base.ref
        mandatory_reviewers = []
        required_reviewers = 0
        try:
            branch: Branch = pull_request.head.repo.get_branch(branch_name)
            branch_protection: BranchProtection = branch.get_protection()
            branch_required_pull_request_reviews: RequiredPullRequestReviews = branch_protection.required_pull_request_reviews
            return branch_required_pull_request_reviews
        except GithubException as e:
            logging.warning(f'Failed to fetch branch protection information for {branch_name}: {e}')
        return required_reviewers, mandatory_reviewers

    def get_pull_requests_for_repo(self, repository: Repository) -> PaginatedList[PullRequest]:
        return repository.get_pulls(state='open', sort='created')

    def get_reviewers_info(self, pull_request: PullRequest, current_user: str) -> Optional[ReviewersInfo]:
        try:
            branch_required_reviews: RequiredPullRequestReviews = self.get_branch_requested_reviewers(pull_request)
            reviews: PaginatedList[PullRequestReview] = pull_request.get_reviews()

            return ReviewersInfo(pull_request=pull_request, reviews=reviews, branch_required_reviews=branch_required_reviews, current_user=current_user)
        except GithubException as e:
            logging.warning(f'Failed to fetch PR reviewers information for repository {pull_request.head.repo}: {e}')
            return None

    def _adjust_connection_pool_size(self, min_needed: int):
        needed = int(min_needed * 1.5)
        if needed > self.pool_size:
            self.pool_size = needed
            self.github.close()
            self.github = Github(self.github_pat, pool_size=self.pool_size)
