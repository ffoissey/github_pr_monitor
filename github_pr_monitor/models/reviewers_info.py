from typing import List, Optional

from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestReview import PullRequestReview
from github.RequiredPullRequestReviews import RequiredPullRequestReviews


class ReviewersInfo:
    CHANGED_REQUESTED = 'CHANGES_REQUESTED'
    APPROVED = 'APPROVED'

    def __init__(self, pull_request: PullRequest, reviews: PaginatedList[PullRequestReview],
                 branch_required_reviews: Optional[RequiredPullRequestReviews], current_user: str):
        self.pull_request = pull_request
        self.reviews = reviews
        self.branch_required_reviews = branch_required_reviews
        self.current_user = current_user

        self.mandatory_reviewers = self._get_mandatory_reviewers()
        self.has_current_user_reviewed = self._has_user_reviewed()
        self.has_current_user_requested = self._has_user_requested_changes()
        self.review_statuses = self._get_review_statuses()
        self.number_of_reviews = len(self.review_statuses)
        self.number_of_completed_reviews = sum(status == self.APPROVED for status in self.review_statuses.values())
        self.number_of_requested_reviewers = self._get_number_of_requested_reviewers()
        self.is_mandatory = current_user in self.mandatory_reviewers

    def _get_mandatory_reviewers(self):
        mandatory_reviewers = set()

        if self.branch_required_reviews is not None and self.branch_required_reviews.dismissal_users is not None:
            mandatory_reviewers.update(user.login for user in self.branch_required_reviews.dismissal_users)

        if self.pull_request.maintainer_can_modify:
            mandatory_reviewers.add(self.pull_request.user.login)

        mandatory_reviewers.update(request.login for request in self.pull_request.get_review_requests()[0])
        return mandatory_reviewers

    def _has_user_reviewed(self):
        return any(review.user.login == self.current_user for review in self.reviews)

    def _has_user_requested_changes(self):
        return any(review.user.login == self.current_user and review.state == self.CHANGED_REQUESTED
                   for review in self.reviews)

    def _get_review_statuses(self):
        return {review.user.login: review.state for review in self.reviews}

    def _get_number_of_requested_reviewers(self):
        branch_count = self.branch_required_reviews.required_approving_review_count if self.branch_required_reviews else 0
        return max(len(self.pull_request.requested_reviewers), branch_count)
