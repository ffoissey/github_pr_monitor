import logging
from typing import List, Optional

from github import Github, GithubException
from github.Auth import Token
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.Repository import Repository

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

    def get_branch_requested_reviewers(self, owner: str, repo: str, branch: str) -> int:
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            branch = repository.get_branch(branch)
            protection = branch.get_protection().required_pull_request_reviews
            required_reviewers = protection.required_approving_review_count if protection else 0
            return required_reviewers
        except GithubException as e:
            logging.warning(f'Failed to fetch branch protection information for {branch}: {e}')
            return 0

    def get_pull_requests_for_repo(self, owner: str, repo: str) -> PaginatedList[PullRequest]:
        repository = self.github.get_repo(f"{owner}/{repo}")
        return repository.get_pulls(state='open', sort='created')

    def get_reviewers_info(self, owner: str, repo: str, id: int, base_branch: str) -> Optional[ReviewersInfo]:
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            pull_request = repository.get_pull(id)

            reviews = pull_request.get_reviews()
            requested_reviewers = pull_request.get_review_requests()[0]

            current_user = self.get_current_user_login()
            has_current_user_reviewed = any(review.user.login == current_user for review in reviews)
            has_current_user_requested = any(
                review.user.login == current_user and review.state == 'CHANGES_REQUESTED' for review in reviews)
            review_statuses = {review.user.login: review.state for review in reviews}
            number_of_reviews = len(set(review_statuses.keys()))
            number_of_completed_reviews = len(
                set([review.user.login for review in reviews if review.state == 'APPROVED']))
            number_of_branch_requested_reviewers = self.get_branch_requested_reviewers(owner, repo, base_branch)
            number_of_requested_reviewers = max(requested_reviewers.totalCount, number_of_branch_requested_reviewers)

            return ReviewersInfo(
                number_of_reviews=number_of_reviews,
                number_of_completed_reviews=number_of_completed_reviews,
                number_of_requested_reviewers=number_of_requested_reviewers,
                has_current_user_reviewed=has_current_user_reviewed,
                has_current_user_requested=has_current_user_requested
            )
        except GithubException as e:
            logging.warning(f'Failed to fetch PR reviewers information for repository {repo}: {e}')
            return None

    def _adjust_connection_pool_size(self, min_needed: int):
        needed = int(min_needed * 1.5)
        if needed > self.pool_size:
            self.pool_size = needed
            self.github.close()
            self.github = Github(self.github_pat, pool_size=self.pool_size)
