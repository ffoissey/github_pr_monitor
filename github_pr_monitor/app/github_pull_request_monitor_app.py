import http
import logging
import threading
import webbrowser
from typing import Optional, List, Callable, Any

from github import GithubException
from rumps import rumps, MenuItem, separator, timer

from github_pr_monitor.app.repository_info_fetcher import RepositoryInfoFetcher
from github_pr_monitor.config.config_manager import ConfigManager
from github_pr_monitor.models.pull_request_info import PullRequestInfo
from github_pr_monitor.models.repository_info import RepositoryInfo
from github_pr_monitor.security.keyring_manager import KeyringManager


# TODO: REMOVE FOR PRODUCTION
# rumps.debug_mode(True)

# TODO: NOTIFICATION WHIT NUMBER OF PR TO REVIEW EACH HOUR
# TODO: MENU FOR SETTINGS


class GithubPullRequestMonitorApp(rumps.App):
    APP_NAME: str = "PR Monitor"

    REFRESH_MENU: str = "Force Refresh"
    PAT_SETTING_MENU: str = "Set Github Personal Access Token"
    REPOSITORY_FILTER_SETTING_MENU: str = "Set Repository Search Filter"
    QUIT_MENU = "Quit"

    DIALOG_HEIGHT: int = 30
    DIALOG_WIDTH: int = 400

    REFRESH_DELAY: int = 600

    def __init__(self, repo_search_filter: Optional[str] = None, ask_pat: Optional[bool] = False):
        super(GithubPullRequestMonitorApp, self).__init__(self.APP_NAME)
        self.config_manager = ConfigManager()
        self.keyring_manager = KeyringManager()
        self.menu_callbacks = {
            self.REFRESH_MENU: self.refresh,
            self.PAT_SETTING_MENU: self.ask_for_github_pat,
            self.REPOSITORY_FILTER_SETTING_MENU: self.ask_for_repository_search_filter,
            self.QUIT_MENU: self.quit
        }
        self.repo_search_filter = repo_search_filter or self.config_manager.get_repo_search_filter()

        if ask_pat is True or self.keyring_manager.get_github_pat() is None:
            self.ask_for_github_pat()
        self.are_all_buttons_disabled = False
        self.repositories_info = []
        self._reset_menu()
        self.pull_request_processor = RepositoryInfoFetcher()
        self.refresh_lock = threading.Lock()
        # TODO: option for refresh time
        self.check_update_timer = rumps.Timer(self.check_if_update_is_ready, 1)
        self.processing_done = False
        self.timer = rumps.Timer(self.on_tick, self.REFRESH_DELAY)
        self.timer.start()

    def on_tick(self, _):
        self.refresh()

    def quit(self, _=None):
        threading.Thread(target=self.quit_app, daemon=True).start()

    def quit_app(self):
        self.menu[self.QUIT_MENU].title = "Quitting..."
        self.title = f"{self.APP_NAME} 👋 (Quitting)"
        self._disable_all_buttons()
        self.pull_request_processor.set_abort_process_flag(True)
        self.pull_request_processor.waiting_for_stop_processing()
        rumps.quit_application()

    def refresh(self, _=None):
        threading.Thread(target=self.update_menu, daemon=True).start()
        self.check_update_timer.start()

    def ask_for_github_pat(self, _=None):
        self._open_dialog(title="GitHub Personal Access Token", message="Please enter your GitHub PAT:",
                          callback=self.keyring_manager.set_github_pat)

    def ask_for_repository_search_filter(self, _=None):
        self._open_dialog(title="Repository Search Filter", message="Please enter a filter:",
                          callback=self.config_manager.set_repo_search_filter, default_text=self.repo_search_filter)

    @staticmethod
    def on_pr_click(sender):
        webbrowser.open(sender.url)

    def update_menu(self):
        self.pull_request_processor.set_abort_process_flag(True)
        with self.refresh_lock:
            self.processing_done = False
            self.pull_request_processor.set_abort_process_flag(False)
            # self._render(self._reset_menu)
            self._reset_menu()
            self._disable_button(self.REFRESH_MENU)
            self.menu.get(self.REFRESH_MENU).title = 'Refreshing… ⏳'
            self.title = f'{self.APP_NAME} ⏳'
            try:
                self.repositories_info = self.pull_request_processor.get_repositories_info(
                    self.keyring_manager.get_github_pat(), self.repo_search_filter)
                # repositories_info = self.pull_request_processor.get_repositories_info(
                #     self.keyring_manager.get_github_pat(), self.repo_search_filter)
                # self._update_repositories(repositories_info)
            except GithubException as e:
                if e.status == http.HTTPStatus.UNAUTHORIZED:
                    self.title = f'{self.APP_NAME} ⚠️ (Invalid PAT)'
                logging.error(e.message)

            self.menu.get(self.REFRESH_MENU).title = self.REFRESH_MENU
            if self.are_all_buttons_disabled is False:
                self._enable_button(self.REFRESH_MENU)
            self.processing_done = True

    def check_if_update_is_ready(self, _):
        if self.processing_done:
            self.check_update_timer.stop()
            self._update_repositories()

    def _update_repositories(self):
        is_urgent = False
        for repository_info in self.repositories_info:
            if len(repository_info.pull_requests_info) > 0:
                submenu = MenuItem(repository_info.name)
                submenu.title = f"{repository_info.status} {repository_info.name}"
                self.menu.add(submenu)
                self._update_pull_requests(submenu, repository_info.pull_requests_info)
                if repository_info.is_urgent is True:
                    is_urgent = True
        self.title = f'{self.APP_NAME} 🔔' if is_urgent else self.APP_NAME

    def _update_pull_requests(self, submenu: MenuItem, prs_info: List[PullRequestInfo]):
        for pr_info in prs_info:
            title: str = self._format_pr_title(pr_info)
            item = submenu.get(title)
            if item is None:
                item = MenuItem(title=title, callback=self.on_pr_click)
                item.set_callback(self.on_pr_click)
                item.url = pr_info.url
                submenu.add(item)
            item.title = title

    @staticmethod
    def _format_pr_title(pr_info: PullRequestInfo):
        return f"{pr_info.status} ({pr_info.reviewers_info.number_of_reviews}👁️) " \
               f"[{pr_info.reviewers_info.number_of_completed_reviews} " \
               f"/ {pr_info.reviewers_info.number_of_requested_reviewers}] " \
               f"➤ {pr_info.title}"

    def _reset_menu(self):
        self.menu.clear()
        for title, callback in self.menu_callbacks.items():
            self.menu.add(MenuItem(title=title, callback=callback))
        self.menu.add(separator)

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

    def _set_button_callback(self, title: str, cb: Any):
        button = self.menu.get(title)
        if button is not None and hasattr(button, 'set_callback'):
            button.set_callback(cb)
