from github_pr_monitor.models.reviewers_info import ReviewersInfo


class PullRequestInfo:
    def __init__(self, title: str, url: str, id: int, is_draft: bool, reviewers_info: ReviewersInfo):
        self.title = title
        self.url = url
        self.id = id
        self.is_draft = is_draft
        self.reviewers_info = reviewers_info

    @property
    def status(self) -> str:
        if self.is_draft:
            return "📃"
        elif self.reviewers_info.number_of_completed_reviews >= self.reviewers_info.number_of_requested_reviewers:
            return "🟡"
        elif self.reviewers_info.has_current_user_reviewed:
            return "💬" if self.reviewers_info.has_current_user_requested else "✅"
        else:
            return "🔴"
