class ReviewersInfo:
    def __init__(self, number_of_reviews: int, number_of_completed_reviews: int,
                 number_of_requested_reviewers: int, has_current_user_reviewed: bool,
                 has_current_user_requested: bool):
        self.number_of_reviews = number_of_reviews
        self.number_of_completed_reviews = number_of_completed_reviews
        self.number_of_requested_reviewers = number_of_requested_reviewers
        self.has_current_user_reviewed = has_current_user_reviewed
        self.has_current_user_requested = has_current_user_requested
