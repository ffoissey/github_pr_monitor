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
        return f"{'❗️' if self.reviewers_info.is_mandatory else ''}" \
               f"{self.status}{'👤' if self.is_author else ''}\t" \
               f"({self.reviewers_info.number_of_reviews}👁️)" \
               f"[{self.reviewers_info.number_of_completed_reviews} " \
               f"/ {self.reviewers_info.number_of_requested_reviewers}]\t➤\t" \
               f"{self.title}"

    @property
    def status(self) -> str:
        if self.is_draft:
            return "📃"
        elif self.reviewers_info.has_current_user_requested:
            return "💬"
        elif self.reviewers_info.has_current_user_reviewed and \
                (self.is_author is False or self.reviewers_info.is_mandatory):
            return "✅"
        elif self.reviewers_info.is_mandatory or \
                (self.is_author is False and
                 self.reviewers_info.number_of_completed_reviews < self.reviewers_info.number_of_requested_reviewers):
            return "🔴"
        else:
            return "🟡"
