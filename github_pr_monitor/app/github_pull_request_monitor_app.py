import http
import logging
import threading
import webbrowser
from datetime import timedelta, datetime
from typing import Optional, List, Callable, Any, Dict, Tuple

import requests
from github import GithubException
from rumps import MenuItem, separator, notification, Timer, Window, quit_application, App

from github_pr_monitor.app.repository_info_fetcher import RepositoryInfoFetcher
from github_pr_monitor.config import THREAD_MANAGER
from github_pr_monitor.constants.app_setting_constants import DIALOG_WIDTH, DIALOG_HEIGHT, DEFAULT_REFRESH_DELAY, \
    UPDATE_CHECKER_DELAY, DEFAULT_NOTIFICATION_DELAY
from github_pr_monitor.constants.display_constants import REFRESH_MENU, SETTINGS_MENU, QUIT_MENU, PAT_SETTING_MENU, \
    REPOSITORY_FILTER_SETTING_MENU, REFRESH_DELAY_SETTING_MENU, INVALID_PAT_MSG, NETWORK_ERROR_MSG, DEFAULT_ERROR, \
    QUITTING, APP_QUITTING, APP_NAME, REFRESHING
from github_pr_monitor.constants.emojis import NOTIFICATION_EMOJI, NOTHING_TO_DO_EMOJI, NO_PR_EMOJI, ERROR_EMOJI, \
    IN_PROGRESS_EMOJI, PR_URGENT_EMOJI, PR_COMMENT_EMOJI, AUTHOR_EMOJI
from github_pr_monitor.managers.config_manager import ConfigManager
from github_pr_monitor.models.pull_request_info import PullRequestInfo
from github_pr_monitor.models.repository_info import RepositoryInfo
from github_pr_monitor.security.keyring_manager import KeyringManager


# TODO: Modify Notification timing
# TODO: Enable/Disable Notification
# TODO: Notification icon does not work
# TODO: Log file
# TODO: Foreground message dialog
# TODO: Clear cache if force refresh

class GithubPullRequestMonitorApp(App):

    def __init__(self, repo_search_filter: Optional[str] = None, ask_pat: Optional[bool] = False):
        super(GithubPullRequestMonitorApp, self).__init__(APP_NAME)
        self.config_manager = ConfigManager()
        self.keyring_manager = KeyringManager()
        self.repository_info_fetcher = RepositoryInfoFetcher()
        self.menu_callbacks = self._setup_menu_callbacks()
        self.setting_submenu_callbacks = self._setup_settings_callbacks()
        self.thread_manager = THREAD_MANAGER
        self.repositories_info: List[RepositoryInfo] = []
        self.are_all_buttons_disabled = False
        self.processing_done = True
        self.invalid_pat = False
        self.connection_error = False
        self.refresh_lock = threading.Lock()

        # Settings init
        self.repo_search_filter = repo_search_filter or self.config_manager.get_repo_search_filter()
        self.notification_delay = DEFAULT_NOTIFICATION_DELAY
        if ask_pat is True or self.keyring_manager.get_github_pat() is None:
            self.ask_for_github_pat()
        self.refresh_delay = self.config_manager.get_refresh_time() or DEFAULT_REFRESH_DELAY

        # Timers init

        # change logic to set different time
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        initial_delay = (next_hour - now).total_seconds()

        self.check_update_timer = Timer(self._check_if_update_is_ready, UPDATE_CHECKER_DELAY)
        self.refresh_timer = Timer(self.refresh, self.refresh_delay)
        self.hourly_notification_timer = Timer(self.start_hourly_notifications, initial_delay)

        self.refresh_timer.start()
        self.hourly_notification_timer.start()

    # Buttons Callbacks

    def refresh(self, _=None) -> None:
        self.processing_done = False
        self.repository_info_fetcher.set_abort_process_flag(True)
        with self.refresh_lock:
            self.repository_info_fetcher.set_abort_process_flag(False)
            self.processing_done = False
            self.invalid_pat = False
            self.connection_error = False
            self._reset_menu()
            self._disable_button(REFRESH_MENU)
            self.menu.get(REFRESH_MENU).title = REFRESHING
            self.title = f'{APP_NAME} {IN_PROGRESS_EMOJI}'
            self.thread_manager.start_thread(self._fetch_repositories_info, daemon=True)
        self.check_update_timer.start()

    def quit(self, _=None) -> None:
        self._prepare_to_quit()
        self.thread_manager.start_thread(self._quit_application, daemon=True)

    def ask_for_github_pat(self, _=None) -> None:
        self._open_dialog(title="GitHub Personal Access Token", message="Please enter your GitHub PAT",
                          callback=self.keyring_manager.set_github_pat, secure=True)

    def ask_for_repository_search_filter(self, _=None) -> None:
        self._open_dialog(title="Repository Search Filter", message="Please enter a filter",
                          callback=self._set_repo_search_filter, default_text=self.repo_search_filter)

    def ask_for_refresh_delay(self, _=None) -> None:
        validator: Callable[[str], Tuple[bool, str]] = lambda input_value: (
            int(input_value) > 1, None) \
            if input_value.isdigit() \
            else (False, "Please enter an integer value greater than 0")

        self._open_dialog(title="Refresh Delay", message="Please enter a delay (in minutes)",
                          callback=self._set_refresh_time, default_text=str(self.refresh_delay // 60),
                          validator_callback=validator)

    # Notification Status

    def start_hourly_notifications(self, _):
        self.send_hourly_notification()

        self.hourly_notification_timer.stop()
        self.hourly_notification_timer = Timer(self.send_hourly_notification, self.notification_delay)
        self.hourly_notification_timer.start()

    def send_hourly_notification(self, _=None):
        with self.refresh_lock:
            prs: List[PullRequestInfo] = [pr for repo_info in self.repositories_info for pr in
                                          repo_info.pull_requests_info]
            pr_to_review = len([pr for pr in prs if pr.status == PR_URGENT_EMOJI])
            pr_commented = len([pr for pr in prs if pr.status == PR_COMMENT_EMOJI])
            pr_in_progress = len([pr for pr in prs if pr.is_author])

        notification_message: str = ''
        if pr_to_review > 0:
            notification_message += f"{PR_URGENT_EMOJI} PRs to review: \t\t{pr_to_review}\n"
        if pr_commented > 0:
            notification_message += f"{PR_COMMENT_EMOJI} PRs commented: \t{pr_commented}\n"
        if pr_in_progress > 0:
            notification_message += f"{AUTHOR_EMOJI} PRs in progress: \t{pr_in_progress}\n"
        if notification_message:
            notification("Pull Requests Status", None, notification_message,
                         sound=True, icon="../assets/github_pr_monitor.icns")

    # Setup Callbacks

    def _setup_menu_callbacks(self) -> Dict[str, Optional[Callable[[Any], None]]]:
        return {
            REFRESH_MENU: self.refresh,
            SETTINGS_MENU: None,
            QUIT_MENU: self.quit
        }

    def _setup_settings_callbacks(self) -> Dict[str, Optional[Callable[[Any], None]]]:
        return {
            PAT_SETTING_MENU: self.ask_for_github_pat,
            REPOSITORY_FILTER_SETTING_MENU: self.ask_for_repository_search_filter,
            REFRESH_DELAY_SETTING_MENU: self.ask_for_refresh_delay
        }

    @staticmethod
    def _open_web_link(sender) -> None:
        webbrowser.open(sender.url)

    # Timer callback

    def _check_if_update_is_ready(self, _) -> None:
        if self.processing_done:
            self.check_update_timer.stop()
            self._reset_menu()
            self._update_repositories()

    # Update UI functions

    def _update_repositories(self) -> None:
        self._set_title_based_on_connection_status()

        if self.connection_error:
            return

        self.menu.add(separator)
        is_urgent, has_no_pr = self._populate_menu_with_repos()

        if is_urgent is True:
            self.title += NOTIFICATION_EMOJI
        elif has_no_pr is True:
            self.title += NO_PR_EMOJI
        else:
            self.title += NOTHING_TO_DO_EMOJI

    def _set_title_based_on_connection_status(self) -> None:
        self.title = APP_NAME + ' '
        if self.connection_error:
            self.title += f'{ERROR_EMOJI}️ {INVALID_PAT_MSG if self.invalid_pat else NETWORK_ERROR_MSG}'

    def _populate_menu_with_repos(self) -> Tuple[bool, bool]:
        is_urgent = False
        has_no_pr = True
        for repository_info in self.repositories_info:
            if repository_info.pull_requests_info:
                has_no_pr = False
                title: str = repository_info.format_repo_title()
                submenu = MenuItem(title, callback=self._open_web_link)
                submenu.url = repository_info.prs_page_url
                self.menu.add(submenu)
                self._update_pull_requests(submenu, repository_info.pull_requests_info)
                is_urgent |= repository_info.is_urgent
        return is_urgent, has_no_pr

    def _update_pull_requests(self, submenu: MenuItem, prs_info: List[PullRequestInfo]) -> None:
        for pr_info in prs_info:
            title: str = pr_info.format_pr_title()
            item = MenuItem(title, callback=self._open_web_link)
            item.url = pr_info.url
            submenu.add(item)

    def _reset_menu(self) -> None:
        self.menu.clear()
        self.title = APP_NAME
        settings_menu = MenuItem(SETTINGS_MENU)
        for title, callback in self.setting_submenu_callbacks.items():
            settings_menu.add(MenuItem(title=title, callback=callback))
        for title, callback in self.menu_callbacks.items():
            if title == SETTINGS_MENU:
                self.menu.add(settings_menu)
            else:
                self.menu.add(MenuItem(title=title, callback=callback))

    # Fetch Repository Information

    def _fetch_repositories_info(self) -> None:
        try:
            self.repositories_info = self.repository_info_fetcher.get_repositories_info(
                self.keyring_manager.get_github_pat(), self.repo_search_filter)
        except GithubException as e:
            if e.status == http.HTTPStatus.UNAUTHORIZED:
                self.connection_error = True
                self.invalid_pat = True
            logging.error(e.message or DEFAULT_ERROR)
        except requests.exceptions.ConnectionError as e:
            self.connection_error = True
            logging.error(e or DEFAULT_ERROR)
        except Exception as e:
            logging.error(e or DEFAULT_ERROR)

        self.menu.get(REFRESH_MENU).title = REFRESH_MENU
        if self.are_all_buttons_disabled is False:
            self._enable_button(REFRESH_MENU)
        self.processing_done = True

    # Configuration Setters

    def _set_repo_search_filter(self, repo_search_filter: str) -> None:
        self.repo_search_filter = repo_search_filter.lower() if repo_search_filter != '' else None
        self.config_manager.set_repo_search_filter(self.repo_search_filter)

    def _set_repo_github_pat(self, github_pat: str) -> None:
        self.keyring_manager.set_github_pat(github_pat if github_pat != '' else None)

    def _set_refresh_time(self, refresh_time_in_minutes_string: str) -> None:
        try:
            refresh_time_in_seconds: int = int(refresh_time_in_minutes_string) * 60
            if refresh_time_in_seconds <= 0:
                raise ValueError("Refresh time should be greater or equal than 1 minute")
            self.refresh_delay = refresh_time_in_seconds
            self.refresh_timer.interval = self.refresh_delay
            self.config_manager.set_refresh_time(self.refresh_delay)
        except Exception as e:
            logging.warning(e)

    # Dialog Management

    def _open_dialog(self, title: str, message: str, callback: Callable[[str], None],
                     validator_callback: Callable[[str], Tuple[bool, str]] = lambda _: (True, ""),
                     default_text: str = '', secure: bool = False, do_refresh: bool = True) -> None:

        input_is_valid: bool = False
        error_message: str = ""
        while not input_is_valid:
            response = Window(
                title=title,
                message=f"{message}{(' - ' + ERROR_EMOJI + ' ' + error_message) if error_message else ''}:",
                default_text=f"{default_text or ''}",
                ok="Submit",
                cancel="Cancel",
                secure=secure,
                dimensions=(DIALOG_WIDTH, DIALOG_HEIGHT)
            ).run()
            if response.clicked:
                value: str = response.text.strip()
                is_valid, error_message = validator_callback(value)
                if is_valid:
                    input_is_valid = True
                    if value != default_text:
                        callback(value)
                        if do_refresh:
                            self.refresh()
            else:
                break

    # Buttons Management

    def _disable_all_buttons(self) -> None:
        self.are_all_buttons_disabled = True
        for button_title in self.menu.keys():
            self._set_button_callback(button_title, None)

    def _enable_button(self, title: str) -> None:
        self._set_button_callback(title, self.menu_callbacks.get(title, None))

    def _disable_button(self, title: str) -> None:
        self._set_button_callback(title, None)

    def _set_button_callback(self, title: str, cb: Optional[Callable[[Any], None]]):
        button = self.menu.get(title)
        if button is not None and hasattr(button, 'set_callback'):
            button.set_callback(cb)

    # Exit Functions

    def _prepare_to_quit(self) -> None:
        self.repository_info_fetcher.set_abort_process_flag(True)
        self._update_ui_for_quitting()
        self.refresh_timer.stop()

    def _update_ui_for_quitting(self) -> None:
        self.menu[QUIT_MENU].title = QUITTING
        self.title = APP_QUITTING
        self._disable_all_buttons()

    def _quit_application(self) -> None:
        self.thread_manager.wait_for_all_threads()
        quit_application()
