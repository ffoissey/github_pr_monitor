import threading
from github import Github, GithubException
from typing import Optional, Callable, List

import rumps
import keyring
import argparse
import logging
import webbrowser
import json
import os

from github.PullRequest import PullRequest
from github.Repository import Repository
from rumps import MenuItem

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


# TODO: REMOVE FOR PRODUCTION
# rumps.debug_mode(True)

# TODO: NOTIFICATION WHIT NUMBER OF PR TO REVIEW EACH HOUR
# TODO: MENU FOR SETTINGS
# TODO: IF NO PAT, WARNING
class ReviewersInfo:
    def __init__(self, number_of_reviews: int, number_of_completed_reviews: int,
                 number_of_requested_reviewers: int, has_current_user_reviewed: bool,
                 has_current_user_requested: bool):
        self.number_of_reviews = number_of_reviews
        self.number_of_completed_reviews = number_of_completed_reviews
        self.number_of_requested_reviewers = number_of_requested_reviewers
        self.has_current_user_reviewed = has_current_user_reviewed
        self.has_current_user_requested = has_current_user_requested


class PullRequestInfo:
    def __init__(self, title: str, url: str, id: int, is_draft: bool, reviewers_info: ReviewersInfo):
        self.title = title
        self.url = url
        self.id = id
        self.is_draft = is_draft
        self.reviewers_info = reviewers_info

    @property
    def status(self):
        if self.is_draft:
            return "📃"
        elif self.reviewers_info.number_of_reviews >= self.reviewers_info.number_of_requested_reviewers:
            return "🟡"
        elif self.reviewers_info.has_current_user_reviewed:
            return "💬" if self.reviewers_info.has_current_user_requested else "✅"
        else:
            return "🔴"


class RepositoryInfo:
    def __init__(self, name: str, pull_requests_info: List[PullRequestInfo]):
        self.name = name
        self.pull_requests_info = pull_requests_info
        self.status, self.is_urgent = self._get_highest_priority_status()

    def _get_highest_priority_status(self):
        priority_order = ['🔴', '💬', '🟡', '🟢', '⚪']
        default_status = priority_order[-1]
        highest_status = default_status
        is_urgent = False

        for pr in self.pull_requests_info:
            pr_status = pr.status if pr else default_status
            if pr_status in priority_order:
                is_current_higher_priority = priority_order.index(pr_status) < priority_order.index(highest_status)
                if is_current_higher_priority:
                    highest_status = pr_status
                    is_urgent = pr_status in ['🔴', '💬']
                    if pr_status == '🔴':
                        break

        return highest_status, is_urgent


class PullRequestApp(rumps.App):
    APP_NAME: str = "PR Monitor"

    REFRESH_MENU: str = "Force Refresh"
    PAT_SETTING_MENU: str = "Set Github Personal Access Token"
    REPOSITORY_FILTER_SETTING_MENU: str = "Set Repository Search Filter"
    QUIT_MENU = "Quit"

    DIALOG_HEIGHT: int = 30
    DIALOG_WIDTH: int = 300

    def __init__(self, repo_search_filter: Optional[str] = None, ask_pat: Optional[bool] = False):
        super(PullRequestApp, self).__init__(self.APP_NAME)
        self.config_manager = ConfigManager()
        self.menu_callbacks = {
            self.REFRESH_MENU: self.refresh,
            self.PAT_SETTING_MENU: self.ask_for_github_pat,
            self.REPOSITORY_FILTER_SETTING_MENU: self.ask_for_repository_search_filter,
            self.QUIT_MENU: self.quit
        }
        self.repo_search_filter = repo_search_filter or self.config_manager.get_repo_search_filter()
        if ask_pat is True or KeyringInterface.get_github_pat() is None:
            self.ask_for_github_pat()
        self.are_all_buttons_disabled = False
        self._reset_menu()
        self.pull_request_processor = PullRequestProcessor()
        self.refresh_lock = threading.Lock()
        # TODO: option for refresh time
        self.timer = rumps.Timer(self.on_tick, 600)
        self.timer.start()
        # rumps.notification("Mon Titre", "Message de test", "Mon sous-titre", sound=True)

    def on_tick(self, _):
        self.refresh()

    def quit(self, _=None):
        threading.Thread(target=self.quit_app, daemon=True).start()

    def quit_app(self):
        self.menu[self.QUIT_MENU].title = "Quitting..."
        self.title = "PR Monitor 👋 (Quitting)"
        self._disable_all_buttons()
        self.pull_request_processor.set_abort_process_flag(True)
        self.pull_request_processor.waiting_for_stop_processing()
        rumps.quit_application()

    def refresh(self, _=None):
        threading.Thread(target=self.update_menu, daemon=True).start()

    def ask_for_github_pat(self, _=None):
        self._open_dialog(title="GitHub Personal Access Token", message="Please enter your GitHub PAT:",
                          callback=KeyringInterface.set_github_pat)

    def ask_for_repository_search_filter(self, _=None):
        self._open_dialog(title="Repository Search Filter", message="Please enter a filter:",
                          callback=self.config_manager.set_repo_search_filter, default_text=self.repo_search_filter)

    @staticmethod
    def on_pr_click(sender):
        webbrowser.open(sender.url)

    def update_menu(self):
        self.pull_request_processor.set_abort_process_flag(True)
        with self.refresh_lock:
            self.pull_request_processor.set_abort_process_flag(False)
            self._reset_menu()
            self._disable_button(self.REFRESH_MENU)
            self.menu.get(self.REFRESH_MENU).title = 'Refreshing… ⏳'
            self.title = f'{self.APP_NAME} ⏳'
            repositories_info = self.pull_request_processor.get_repositories_info(self.repo_search_filter)
            self._update_repositories(repositories_info)
            self.menu.get(self.REFRESH_MENU).title = self.REFRESH_MENU
            if self.are_all_buttons_disabled is False:
                self._enable_button(self.REFRESH_MENU)

    def _update_repositories(self, repositories_info: List[RepositoryInfo]):
        for repository_info in repositories_info:
            if len(repository_info.pull_requests_info) == 0:
                continue
            submenu = MenuItem(repository_info.name)
            submenu.title = f"{repository_info.status} {repository_info.name}"

            self.menu.add(submenu)
            self._update_pull_requests(submenu, repository_info.pull_requests_info)
            self.title = f'{self.APP_NAME} 🔔' if repository_info.is_urgent else self.APP_NAME

    def _update_pull_requests(self, submenu: MenuItem, prs_info: List[PullRequestInfo]):
        for pr_info in prs_info:
            title: str = self._format_pr_title(pr_info)
            item = submenu.get(title)
            if item is None:
                item = rumps.MenuItem(title=title, callback=self.on_pr_click)
                item.set_callback(self.on_pr_click)
                item.url = pr_info.url
                submenu.add(item)
            item.title = title

    def _format_pr_title(self, pr_info: PullRequestInfo):
        return f"{pr_info.status} ({pr_info.reviewers_info.number_of_reviews}👁️) " \
               f"[{pr_info.reviewers_info.number_of_completed_reviews} " \
               f"/ {pr_info.reviewers_info.number_of_requested_reviewers}] " \
               f"➤ {pr_info.title}"

    def _reset_menu(self):
        self.menu.clear()
        for title, callback in self.menu_callbacks.items():
            self.menu.add(rumps.MenuItem(title=title, callback=callback))
        self.menu.add(rumps.separator)

    def _open_dialog(self, title: str, message: str, callback: Callable[[str], None], default_text: str = '',
                     do_refresh: bool = True):
        response = rumps.Window(
            title=title,
            message=message,
            default_text=f"{default_text or ''}",
            ok="Submit",
            cancel="Cancel",
            dimensions=(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        ).run()
        if response.clicked:
            callback(response.text.strip())
            if do_refresh is True:
                self.refresh()

    def _disable_all_buttons(self) -> None:
        self.are_all_buttons_disabled = True
        for button_title in self.menu.keys():
            self._set_button_callback(button_title, None)

    def _enable_button(self, title: str):
        self._set_button_callback(title, self.menu_callbacks.get(title, None))

    def _disable_button(self, title: str) -> None:
        self._set_button_callback(title, None)

    def _set_button_callback(self, title: str, cb):
        button = self.menu.get(title)
        if button is not None and hasattr(button, 'set_callback'):
            button.set_callback(cb)

class ConfigManager:
    DEFAULT_DIR: str = '~/Library/Application Support/PRMonitor'
    DEFAULT_FILE_NAME: str = 'config.json'
    REPO_SEARCH_FILTER_KEY: str = 'repo_search_filter'

    def __init__(self, dir_name: str = DEFAULT_DIR, file_name: str = DEFAULT_FILE_NAME):
        self.config_path = self._get_config_path(dir_name, file_name)
        self.config = self._load_config()

    def get_repo_search_filter(self):
        return self._get_config(self.REPO_SEARCH_FILTER_KEY)

    def set_repo_search_filter(self, repo_search_filter: Optional[str]):
        self._set_config(self.REPO_SEARCH_FILTER_KEY, repo_search_filter if repo_search_filter != '' else None)

    def _get_config(self, key: str):
        return self.config.get(key)

    def _set_config(self, key: str, value: str):
        self.config[key] = value
        self._save_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as config_file:
                return json.load(config_file)
        except FileNotFoundError as e:
            logging.warning(f'Error while loading config file: {e}')
            return {}

    def _save_config(self):
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file)

    @staticmethod
    def _get_config_path(dir_name: str = DEFAULT_DIR, file_name: str = DEFAULT_FILE_NAME):
        config_dir = os.path.expanduser(dir_name)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return os.path.join(config_dir, file_name)


class KeyringInterface:
    @staticmethod
    def set_github_pat(token: str) -> None:
        keyring.set_password('github', 'token', token)

    @staticmethod
    def get_github_pat():
        return keyring.get_password('github', 'token')


class GithubAPIFetcher:
    def __init__(self):
        self.github = None

    def connect_to_github(self, token: str):
        self.github = Github(token)

    def get_all_repositories(self, filter_keyword: str = None) -> list:
        filter_keyword = filter_keyword.lower() if filter_keyword else None
        try:
            repos = []
            for repo in self.github.get_user().get_repos():
                if not filter_keyword or (filter_keyword in repo.name.lower()):
                    repos.append(repo)
            return repos
        except GithubException as e:
            logging.error(f'Error fetching repositories: {e}')
            return []

    def get_current_user_login(self) -> str:
        try:
            return self.github.get_user().login
        except GithubException as e:
            logging.error(f'Failed to fetch current GitHub user: {e}')
            return ''

    def get_branch_requested_reviewers(self, owner: str, repo: str, branch: str) -> int:
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            branch = repository.get_branch(branch)
            protection = branch.get_protection().required_pull_request_reviews
            required_reviewers = protection.required_approving_review_count if protection else 0
            return required_reviewers
        except GithubException as e:
            logging.error(f'Failed to fetch branch protection information for {branch}: {e}')
            return 0

    def get_pull_requests_for_repo(self, owner: str, repo: str) -> list:
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            prs = repository.get_pulls(state='open', sort='created')
            return [pr for pr in prs]
        except GithubException as e:
            logging.error(f'Error fetching pull requests for {repo}: {e}')
            return []

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


class PullRequestProcessor(GithubAPIFetcher):
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

    def get_repositories_info(self, repo_search_filter: str) -> List[RepositoryInfo]:
        super().connect_to_github(KeyringInterface.get_github_pat())
        repositories_info: List[RepositoryInfo] = []
        try:
            for repo in super().get_all_repositories(repo_search_filter):
                thread = threading.Thread(target=self._process_repo, args=(repo, repositories_info))
                self.active_threads.append(thread)
                thread.start()

            self.waiting_for_stop_processing()
        finally:
            self.active_threads.clear()
        return sorted(repositories_info, key=lambda repository_info: repository_info.name)

    def _process_repo(self, repo: Repository, repositories_info: List[RepositoryInfo]) -> None:
        repo_name = repo.name
        owner = repo.owner.login
        prs = super().get_pull_requests_for_repo(owner, repo_name)
        pull_requests_info: List[PullRequestInfo] = [self._format_pr_info(owner, pr) for pr in prs]
        pull_requests_info = sorted(pull_requests_info, key=lambda pull_request_info: pull_request_info.id)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch GitHub PRs for repositories matching a keyword.")
    parser.add_argument("-r", "--repo_search_filter", help="Keyword to filter repositories", type=str)
    parser.add_argument("-p", "--pat", help="Set GitHub Personal Access Token", action="store_true")
    args = parser.parse_args()

    app = PullRequestApp(repo_search_filter=args.repo_search_filter, ask_pat=args.pat)
    app.run()
