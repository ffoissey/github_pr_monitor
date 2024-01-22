import http
import logging
import threading
import webbrowser
from typing import Optional, List, Callable, Any

import requests
from github import GithubException
from rumps import rumps, MenuItem, separator

from github_pr_monitor.app.repository_info_fetcher import RepositoryInfoFetcher
from github_pr_monitor.managers.config_manager import ConfigManager
from github_pr_monitor.models.pull_request_info import PullRequestInfo
from github_pr_monitor.security.keyring_manager import KeyringManager


# rumps.debug_mode(True)

# TODO: NOTIFICATION WITH NUMBER OF PR TO REVIEW EACH HOUR
# TODO: Log file
# TODO: foreground message console

class GithubPullRequestMonitorApp(rumps.App):
    APP_NAME: str = "PR Monitor"

    REFRESH_MENU: str = "Force Refresh"
    SETTINGS_MENU: str = "Settings"
    QUIT_MENU: str = "Quit"

    DEFAULT_ERROR: str = "Unexpected Error"

    PAT_SETTING_MENU: str = "Github Personal Access Token"
    REPOSITORY_FILTER_SETTING_MENU: str = "Repository Search Filter"
    REFRESH_DELAY_SETTING_MENU: str = "Refresh Delay"

    DIALOG_HEIGHT: int = 25
    DIALOG_WIDTH: int = 500

    DEFAULT_REFRESH_DELAY: int = 300
    UPDATE_CHECKER_DELAY: int = 1

    def __init__(self, repo_search_filter: Optional[str] = None, ask_pat: Optional[bool] = False):
        super(GithubPullRequestMonitorApp, self).__init__(self.APP_NAME)
        self.config_manager = ConfigManager()
        self.keyring_manager = KeyringManager()
        self.repository_info_fetcher = RepositoryInfoFetcher()
        self.menu_callbacks = self.setup_menu_callbacks()
        self.setting_submenu_callbacks = self.setup_settings_callbacks()
        self.repositories_info = []
        self.are_all_buttons_disabled = False
        self.processing_done = True
        self.invalid_pat = False
        self.connection_error = False
        self.refresh_lock = threading.Lock()

        # Settings init
        self.repo_search_filter = repo_search_filter or self.config_manager.get_repo_search_filter()
        if ask_pat is True or self.keyring_manager.get_github_pat() is None:
            self.ask_for_github_pat()
        self.refresh_delay = self.config_manager.get_refresh_time() or self.DEFAULT_REFRESH_DELAY

        # Timers init
        self.check_update_timer = rumps.Timer(self.check_if_update_is_ready, self.UPDATE_CHECKER_DELAY)
        self.refresh_timer = rumps.Timer(self.refresh, self.refresh_delay)

        self.refresh_timer.start()

    def setup_menu_callbacks(self):
        return {
            self.REFRESH_MENU: self.refresh,
            self.SETTINGS_MENU: None,
            self.QUIT_MENU: self.quit
        }

    def setup_settings_callbacks(self):
        return {
            self.PAT_SETTING_MENU: self.ask_for_github_pat,
            self.REPOSITORY_FILTER_SETTING_MENU: self.ask_for_repository_search_filter,
            self.REFRESH_DELAY_SETTING_MENU: self.ask_for_refresh_delay
        }

    def quit(self, _=None):
        threading.Thread(target=self.quit_app, daemon=True).start()

    def quit_app(self):
        self.menu[self.QUIT_MENU].title = "Quitting..."
        self.title = f"{self.APP_NAME} 👋 (Quitting)"
        self._disable_all_buttons()
        self.repository_info_fetcher.set_abort_process_flag(True)
        self.repository_info_fetcher.waiting_for_stop_processing()
        self.refresh_timer.stop()
        rumps.quit_application()

    def refresh(self, _=None):
        self.processing_done = False
        self.check_update_timer.stop()
        self.repository_info_fetcher.set_abort_process_flag(True)
        with self.refresh_lock:
            self.repository_info_fetcher.set_abort_process_flag(False)
            self.processing_done = False
            self.invalid_pat = False
            self.connection_error = False
            self._reset_menu()
            self._disable_button(self.REFRESH_MENU)
            self.menu.get(self.REFRESH_MENU).title = 'Refreshing… ⏳'
            self.title = f'{self.APP_NAME} ⏳'
            threading.Thread(target=self.update_menu, daemon=True).start()
        self.check_update_timer.start()

    def ask_for_github_pat(self, _=None):
        self._open_dialog(title="GitHub Personal Access Token", message="Please enter your GitHub PAT:",
                          callback=self.keyring_manager.set_github_pat, secure=True)

    def ask_for_repository_search_filter(self, _=None):
        self._open_dialog(title="Repository Search Filter", message="Please enter a filter:",
                          callback=self._set_repo_search_filter, default_text=self.repo_search_filter)

    def ask_for_refresh_delay(self, _=None):
        self._open_dialog(title="Refresh Delay", message="Please enter a delay (in minutes):",
                          callback=self._set_refresh_time, default_text=str(self.refresh_delay // 60))

    @staticmethod
    def on_pr_click(sender):
        webbrowser.open(sender.url)

    def update_menu(self):
        try:
            self.repositories_info = self.repository_info_fetcher.get_repositories_info(
                self.keyring_manager.get_github_pat(), self.repo_search_filter)
        except GithubException as e:
            if e.status == http.HTTPStatus.UNAUTHORIZED:
                self.connection_error = True
                self.invalid_pat = True
            logging.error(e.message or self.DEFAULT_ERROR)
        except requests.exceptions.ConnectionError as e:
            self.connection_error = True
            logging.error(e or self.DEFAULT_ERROR)
        except Exception as e:
            logging.error(e or self.DEFAULT_ERROR)

        self.menu.get(self.REFRESH_MENU).title = self.REFRESH_MENU
        if self.are_all_buttons_disabled is False:
            self._enable_button(self.REFRESH_MENU)
        self.processing_done = True

    def check_if_update_is_ready(self, _):
        if self.processing_done:
            self.check_update_timer.stop()
            self._reset_menu()
            self._update_repositories()

    def _update_repositories(self):
        self.title = self.APP_NAME
        if self.connection_error is True:
            self.title += ' ⚠️'
            if self.invalid_pat is True:
                self.title += ' (Invalid PAT)'
            else:
                self.title += ' (Network Error)'
            return

        self.menu.add(separator)
        is_urgent = False
        has_no_pr = True
        for repository_info in self.repositories_info:
            if len(repository_info.pull_requests_info) > 0:
                has_no_pr = False
                submenu = MenuItem(repository_info.name)
                submenu.title = f"{repository_info.status} {repository_info.name}"
                self.menu.add(submenu)
                self._update_pull_requests(submenu, repository_info.pull_requests_info)
                if repository_info.is_urgent is True:
                    is_urgent = True
        if is_urgent is True:
            self.title += ' 🔔'
        elif has_no_pr is True:
            self.title += ' 😴'
            self.menu.add(MenuItem("No pull request to review"))
        else:
            self.title += ' ☑️'

    def _update_pull_requests(self, submenu: MenuItem, prs_info: List[PullRequestInfo]):
        for pr_info in prs_info:
            title: str = pr_info.format_pr_title()
            item = submenu.get(pr_info.format_pr_title())
            if item is None:
                item = MenuItem(title=title, callback=self.on_pr_click)
                item.set_callback(self.on_pr_click)
                item.url = pr_info.url
                submenu.add(item)
            item.title = title

    def _set_repo_search_filter(self, repo_search_filter: str):
        self.repo_search_filter = repo_search_filter.lower() if repo_search_filter != '' else None
        self.config_manager.set_repo_search_filter(self.repo_search_filter)

    def _set_repo_github_pat(self, github_pat: str):
        self.keyring_manager.set_github_pat(github_pat if github_pat != '' else None)

    def _set_refresh_time(self, refresh_time_in_minutes_string: str):
        try:
            refresh_time_in_seconds: int = int(refresh_time_in_minutes_string) * 60
            if refresh_time_in_seconds <= 0:
                raise ValueError("Refresh time should be greater or equal than 1 minute")
            self.refresh_delay = refresh_time_in_seconds
            self.refresh_timer.interval = self.refresh_delay
            self.config_manager.set_refresh_time(self.refresh_delay)
        except Exception as e:
            logging.warning(e)

    def _reset_menu(self):
        self.menu.clear()
        settings_menu = MenuItem(self.SETTINGS_MENU)
        for title, callback in self.setting_submenu_callbacks.items():
            settings_menu.add(MenuItem(title=title, callback=callback))
        for title, callback in self.menu_callbacks.items():
            if title == self.SETTINGS_MENU:
                self.menu.add(settings_menu)
            else:
                self.menu.add(MenuItem(title=title, callback=callback))

    def _open_dialog(self, title: str, message: str, callback: Callable[[str], None], default_text: str = '',
                     secure: bool = False, do_refresh: bool = True):
        response = rumps.Window(
            title=title,
            message=message,
            default_text=f"{default_text or ''}",
            ok="Submit",
            cancel="Cancel",
            secure=secure,
            dimensions=(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        ).run()
        if response.clicked:
            value: str = response.text.strip()
            callback(value)
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
