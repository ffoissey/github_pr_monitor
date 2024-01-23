from github_pr_monitor.constants.emojis import PR_DRAFT_EMOJI, PR_OK_EMOJI, PR_URGENT_EMOJI, PR_IMPORTANT_EMOJI, \
    PR_COMMENT_EMOJI, AUTHOR_EMOJI, REVIEWER_EMOJI
from github_pr_monitor.models.reviewers_info import ReviewersInfo


class PullRequestInfo:

    def __init__(self, title: str, url: str, id: int, is_draft: bool, reviewers_info: ReviewersInfo,
                 is_author: bool):
        self.title = title
        self.url = url
        self.id = id
        self.is_draft = is_draft
        self.reviewers_info = reviewers_info
        self.is_author = is_author

    def format_pr_title(self):
        status: str = f"{self.status}{AUTHOR_EMOJI if self.is_author else '     '} "
        reviewers: str = f"({self.reviewers_info.number_of_reviews}{REVIEWER_EMOJI}️) " \
                         f"[{self.reviewers_info.number_of_completed_reviews} " \
                         f"/ {self.reviewers_info.number_of_requested_reviewers}]"

        return f"{status}{reviewers} ➤\t{self.title}"

    @property
    def status(self) -> str:
        if self.is_draft:
            return PR_DRAFT_EMOJI
        elif self.reviewers_info.has_current_user_requested:
            return PR_COMMENT_EMOJI
        elif self.reviewers_info.has_current_user_reviewed and \
                (self.is_author is False or self.reviewers_info.is_mandatory):
            return PR_OK_EMOJI
        elif self.reviewers_info.is_mandatory or \
                (self.is_author is False and
                 self.reviewers_info.number_of_completed_reviews < self.reviewers_info.number_of_requested_reviewers):
            return PR_URGENT_EMOJI
        else:
            return PR_IMPORTANT_EMOJI
