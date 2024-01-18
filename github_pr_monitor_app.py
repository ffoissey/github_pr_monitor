import threading
from github import Github, GithubException
from typing import Optional

import rumps
import keyring
import argparse
import logging
import webbrowser
import json
import os

from github.PullRequest import PullRequest
from github.Repository import Repository

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

API_GITHUB_BASE_URL = 'https://api.github.com'

DIALOG_HEIGHT: int = 30
DIALOG_WIDTH: int = 300

# TODO: REMOVE FOR PRODUCTION
# rumps.debug_mode(True)

# TODO: NOTIFICATION WHIT NUMBER OF PR TO REVIEW EACH HOUR
# TODO: CONFIG FILE DOES NOT WORK

REFRESH = "Force Refresh"
PAT_SETTING_MENU = "Set Github Personal Access Token"
REPOSITORY_FILTER_SETTING_MENU = "Set Repository Search Filter"
QUIT = "Quit"


class PullRequestApp(rumps.App):
    def __init__(self, repo_search_filter: Optional[str] = None, ask_pat: Optional[bool] = False):
        super(PullRequestApp, self).__init__("PR Monitor")
        self.github = self.connect_to_github(self.get_github_pat())
        self.active_threads = []
        self.are_all_buttons_disabled = False
        self.abort_refresh = False
        self.thread_lock = threading.Lock()
        self.config = self.load_config()
        self.repo_search_filter = self.config.get('repo_filter')
        self.repo_search_filter = None
        self.menu_callbacks = {
            REFRESH: self.refresh,
            PAT_SETTING_MENU: self.ask_for_github_pat,
            REPOSITORY_FILTER_SETTING_MENU: self.ask_for_repository_search_filter,
            QUIT: self.quit
        }
        if repo_search_filter is not None:
            self.repo_search_filter = repo_search_filter
        if ask_pat:
            self.ask_for_github_pat()
        self.reset_menu()
        self.timer = rumps.Timer(self.on_tick, 600)
        self.timer.start()
        # rumps.notification("Mon Titre", "Message de test", "Mon sous-titre", sound=True)
        self.refresh_lock = threading.Lock()

    def on_tick(self, _):
        self.refresh()

    def quit(self, _=None):
        threading.Thread(target=self.quit_app, daemon=True).start()

    def quit_app(self):
        self.abort_refresh = True
        self.menu[QUIT].title = "Quitting..."
        self.title = "PR Monitor 👋 (Quitting)"
        self.disable_all_buttons()
        for thread in self.active_threads:
            thread.join()
        rumps.quit_application()

    def refresh(self, _=None):
        threading.Thread(target=self.update_prs, daemon=True).start()

    def ask_for_github_pat(self, _=None):
        response = rumps.Window(
            title="GitHub PAT Token",
            message="Please enter your GitHub PAT:",
            default_text="",
            ok="Submit",
            cancel="Cancel",
            secure=True,
            dimensions=(DIALOG_WIDTH, DIALOG_HEIGHT)
        ).run()
        if response.clicked:
            self.set_github_pat(response.text)
            self.refresh()

    def ask_for_repository_search_filter(self, _=None):
        response = rumps.Window(
            title="Repository Search Filter",
            message="Please enter a filter:",
            default_text=f"{self.repo_search_filter or ''}",
            ok="Submit",
            cancel="Cancel",
            dimensions=(DIALOG_WIDTH, DIALOG_HEIGHT)
        ).run()
        if response.clicked:
            self.set_repository_search_filter(response.text)
            self.refresh()

    def set_button_callback(self, title: str, cb):
        button = self.menu.get(title)
        if button is not None and hasattr(button, 'set_callback'):
            button.set_callback(cb)

    def disable_button(self, title: str) -> None:
        self.set_button_callback(title, None)

    def disable_all_buttons(self) -> None:
        self.are_all_buttons_disables = True
        for button_title in self.menu.keys():
            self.set_button_callback(button_title, None)

    def enable_button(self, title: str):
        self.set_button_callback(title, self.menu_callbacks.get(title, None))

    def set_repository_search_filter(self, repo_filter: Optional[str] = None):
        self.config['repo_filter'] = repo_filter if repo_filter != '' else None
        self.save_config(self.config)
        self.repo_search_filter = repo_filter

    def reset_menu(self):
        self.menu.clear()
        for title, callback in self.menu_callbacks.items():
            self.menu.add(rumps.MenuItem(title=title, callback=callback))
        self.menu.add(rumps.separator)

    def update_prs(self):
        self.abort_refresh = True
        self.refresh_lock.acquire(blocking=True)
        self.abort_refresh = False
        try:
            self.reset_menu()
            self.disable_button(REFRESH)
            self.menu.get(REFRESH).title = 'Refreshing… ⏳'
            self.title = "PR Monitor ⏳"
            prs_info = {}

            for repo in self.get_all_repositories(self.repo_search_filter):
                thread = threading.Thread(target=self.process_repo, args=(repo, prs_info))
                self.active_threads.append(thread)
                thread.start()

            for thread in self.active_threads:
                thread.join()

            self.update_menu(prs_info)
        finally:
            self.active_threads.clear()
            self.refresh_lock.release()
            self.menu.get(REFRESH).title = REFRESH
            if self.are_all_buttons_disabled is False:
                self.enable_button(REFRESH)

    def update_menu(self, prs_info):
        has_urgent_pr = False
        sorted_repos = sorted(prs_info.keys())
        for repo in sorted_repos:
            prs = prs_info[repo]
            if len(prs) == 0:
                continue
            has_red_prs = any(pr.get('status', '') == '🔴' for pr in prs)
            has_orange_prs = any(pr.get('status', '') in '💬' for pr in prs)
            has_yellow_prs = any(pr.get('status', '') in '🟡' for pr in prs)
            has_green_prs = any(pr.get('status', '') in '🟢' for pr in prs)

            status = '⚪'
            if has_red_prs:
                status = '🔴'
                has_urgent_pr = True
            elif has_orange_prs:
                status = '💬'
                has_urgent_pr = True
            elif has_yellow_prs:
                status = '🟡'
            elif has_green_prs:
                status = '🟢'

            submenu = rumps.MenuItem(repo)
            submenu.title = f"{status} {repo}"
            self.menu.add(submenu)
            print(submenu)
            # TODO: Pas toujours toutes les donnees...
            sorted_prs = sorted(prs, key=lambda pr: pr.get('number', 0))
            for pr in sorted_prs:
                if pr.get('title') is None:
                    continue
                title = f"{pr['status']} ({pr['number_of_reviews']}👁️) [{pr['number_of_completed_reviews']} / {pr['total_reviewers']}] ➤ {pr['title']}"
                item = submenu.get(title)
                if item is None:
                    item = rumps.MenuItem(title=title, callback=self.on_pr_click)
                    item.set_callback(self.on_pr_click)
                    item.url = pr['url']
                    submenu.add(item)
                item.title = title
            if has_urgent_pr:
                self.title = "PR Monitor 🔔"
            else:
                self.title = "PR Monitor"

    def process_repo(self, repo: Repository, prs_info):
        repo_name = repo.name
        owner = repo.owner.login
        prs = self.get_pull_requests_for_repo(owner, repo_name)
        formatted_prs = [self.format_pr_info(owner, pr) for pr in prs]
        prs_info[repo_name] = formatted_prs

    def on_pr_click(self, sender):
        webbrowser.open(sender.url)

    def get_config_path(self):
        config_dir = os.path.expanduser('~/Library/Application Support/PRMonitor')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return os.path.join(config_dir, 'config.json')

    def load_config(self):
        config_path = self.get_config_path()
        try:
            with open(config_path, 'r') as config_file:
                return json.load(config_file)
        except FileNotFoundError as e:
            logging.warning(f'Error while loading config file: {e}')
            return {}

    def save_config(self, config):
        config_path = self.get_config_path()
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file)

    def connect_to_github(self, token):
        return Github(token)

    def set_github_pat(self, token: str) -> None:
        keyring.set_password('github', 'token', token)
        self.connect_to_github(token)

    def get_github_pat(self):
        token = keyring.get_password('github', 'token')
        if token is None:
            self.ask_for_github_pat()
        return token

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

    def get_branch_protection_info(self, owner: str, repo: str, branch: str) -> dict:
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            branch = repository.get_branch(branch)
            protection = branch.get_protection().required_pull_request_reviews
            required_reviewers = protection.required_approving_review_count if protection else 0
            return {'required_reviewers': required_reviewers}
        except GithubException as e:
            logging.error(f'Failed to fetch branch protection information for {branch}: {e}')
            return {'required_reviewers': 0}

    def get_pull_requests_for_repo(self, owner: str, repo: str) -> list:
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            prs = repository.get_pulls(state='open', sort='created')
            return [pr for pr in prs]
        except GithubException as e:
            logging.error(f'Error fetching pull requests for {repo}: {e}')
            return []

    def get_pr_reviewers_info(self, owner: str, repo: str, pr_number: int, base_branch: str) -> dict:
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            pull_request = repository.get_pull(pr_number)

            reviews = pull_request.get_reviews()
            requested_reviewers = pull_request.get_review_requests()[0]  # Returns a tuple of (users, teams)

            current_user = self.get_current_user_login()
            has_current_user_reviewed = any(review.user.login == current_user for review in reviews)
            has_current_user_requested = any(
                review.user.login == current_user and review.state == 'CHANGES_REQUESTED' for review in reviews)
            review_statuses = {review.user.login: review.state for review in reviews}
            number_of_reviews = len(set(review_statuses.keys()))
            number_of_completed_reviews = len(
                set([review.user.login for review in reviews if review.state == 'APPROVED']))

            branch_protection_info = self.get_branch_protection_info(owner, repo, base_branch)
            number_of_requested_reviewers = max(requested_reviewers.totalCount, branch_protection_info['required_reviewers'])

            return {
                'number_of_reviews': number_of_reviews,
                'number_of_completed_reviews': number_of_completed_reviews,
                'number_of_requested_reviewers': number_of_requested_reviewers,
                'has_current_user_reviewed': has_current_user_reviewed,
                'has_current_user_requested': has_current_user_requested
            }
        except GithubException as e:
            logging.warning(f'Failed to fetch PR reviewers information for repository {repo}: {e}')
            return {}

    def format_pr_info(self, owner: str, pr: PullRequest) -> dict:
        if self.abort_refresh is True:
            return {}
        pr_title = pr.title
        pr_url = pr.html_url
        is_draft = pr.draft
        pr_number = pr.number
        base_branch = pr.base.ref
        reviewers_info = self.get_pr_reviewers_info(owner, pr.head.repo.name, pr_number, base_branch)

        status = "🟢"
        if is_draft:
            status = "📃"
        elif reviewers_info['number_of_reviews'] >= reviewers_info['number_of_requested_reviewers']:
            status = "🟡"
        elif reviewers_info['has_current_user_reviewed']:
            status = "💬" if reviewers_info['has_current_user_requested'] else "✅"
        elif not reviewers_info['has_current_user_reviewed']:
            status = "🔴"

        return {
            'title': pr_title,
            'status': status,
            'url': pr_url,
            'number': pr_number,
            'is_draft': is_draft,
            'number_of_reviews': reviewers_info['number_of_reviews'],
            'number_of_completed_reviews': reviewers_info['number_of_completed_reviews'],
            'total_reviewers': reviewers_info['number_of_requested_reviewers'],
            'has_current_user_reviewed': reviewers_info['has_current_user_reviewed'],
            'has_current_user_requested': reviewers_info['has_current_user_requested']
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch GitHub PRs for repositories matching a keyword.")
    parser.add_argument("-r", "--repo_search_filter", help="Keyword to filter repositories", type=str)
    parser.add_argument("-p", "--pat", help="Set GitHub Personal Access Token", action="store_true")
    args = parser.parse_args()

    app = PullRequestApp(repo_search_filter=args.repo_search_filter, ask_pat=args.pat)
    app.run()
