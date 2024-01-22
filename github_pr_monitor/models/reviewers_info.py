from typing import List, Optional

from github.NamedUser import NamedUser
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.PullRequestReview import PullRequestReview
from github.RequiredPullRequestReviews import RequiredPullRequestReviews




class ReviewersInfo:

    CHANGED_REQUESTED = 'CHANGES_REQUESTED'
    APPROVED = 'APPROVED'

    def __init__(self, pull_request: PullRequest, reviews: PaginatedList[PullRequestReview], branch_required_reviews: Optional[RequiredPullRequestReviews], current_user: str):
        mandatory_reviewers: List[str] = []
        if branch_required_reviews is not None and branch_required_reviews.dismissal_users is not None:
            mandatory_reviewers = [user.login for user in branch_required_reviews.dismissal_users]
        if pull_request.maintainer_can_modify is True:
            mandatory_reviewers.append(pull_request.user.login)
        mandatory_reviewers += pull_request.get_review_requests()[0]

        number_of_branch_requested_reviewers = branch_required_reviews.required_approving_review_count or 0

        self.has_current_user_reviewed = any(review.user.login == current_user for review in reviews)
        self.has_current_user_requested = any(
            review.user.login == current_user and review.state == self.CHANGED_REQUESTED for review in reviews)
        review_statuses = {review.user.login: review.state for review in reviews}
        self.number_of_reviews = len(set(review_statuses.keys()))
        self.number_of_completed_reviews = len(
            set([review.user.login for review in reviews if review.state == self.APPROVED]))
        self.number_of_requested_reviewers = max(len(pull_request.requested_reviewers), number_of_branch_requested_reviewers)
        self.mandatory_reviewers = mandatory_reviewers
        self.is_mandatory = current_user in mandatory_reviewers


