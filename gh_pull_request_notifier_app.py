import http
import threading
from typing import Optional

import rumps
import requests
import keyring
import argparse
import logging
import tkinter as tk
from tkinter import simpledialog
import webbrowser
import json
import os
from requests import HTTPError

logging.basicConfig(filename='mon_app.log', level=logging.INFO, format='%(levelname)s: %(message)s')

API_GITHUB_BASE_URL = 'https://api.github.com'

DIALOG_HEIGHT: int = 30
DIALOG_WIDTH: int = 300

rumps.debug_mode(True)

# TODO: NOTIFICATION WHIT NUMBER OF PR TO REVIEW EACH HOUR
# TODO: CONFIG FILE DOES NOT WORK

REFRESH = "Force Refresh"
PAT_SETTING_MENU = "Set Github Personal Access Token"
REPOSITORY_FILTER_SETTING_MENU = "Set Repository Search Filter"

STATIC_MENU = [
    {REFRESH},
    {PAT_SETTING_MENU},
    {REPOSITORY_FILTER_SETTING_MENU}]


class PullRequestApp(rumps.App):
    def __init__(self, repo_search_filter: Optional[str] = None, ask_pat: Optional[bool] = False):
        super(PullRequestApp, self).__init__("PR Monitor")
        self.github_token = None
        self.config = self.load_config()
        self.repo_search_filter = self.config.get('repo_search')
        self.menu_callbacks = {
            REFRESH: self.refresh,
            PAT_SETTING_MENU: self.ask_for_github_pat_token,
            REPOSITORY_FILTER_SETTING_MENU: self.ask_for_repository_search_filter
        }
        if repo_search_filter is not None:
            self.repo_search_filter = repo_search_filter
        if ask_pat:
            self.ask_for_github_pat_token()
        self.reset_menu()
        self.timer = rumps.Timer(self.on_tick, 600)
        self.timer.start()
        # rumps.notification("Mon Titre", "Message de test", "Mon sous-titre", sound=True)

        self.refresh_lock = threading.Lock()

    def on_tick(self, _):
        self.refresh()

    def refresh(self, _=None):
        if self.refresh_lock.locked():
            return
        threading.Thread(target=self.update_prs, daemon=True).start()

    def ask_for_github_pat_token(self, _=None):
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
            self.set_github_pat_token(response.text)
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

    def disable_refresh_button(self):
        self.menu.get(REFRESH).set_callback(None)

    def enable_refresh_button(self):
        self.menu.get(REFRESH).set_callback(self.menu_callbacks[REFRESH])

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
        if not self.refresh_lock.acquire(blocking=False):
            return

        try:
            self.reset_menu()
            self.disable_refresh_button()
            self.menu.get(REFRESH).title = 'Refreshing… ⏳'
            self.title = "PR Monitor ⏳"
            prs_info = {}
            threads = []

            for repo in self.get_all_repositories(self.repo_search_filter):
                thread = threading.Thread(target=self.process_repo, args=(repo, prs_info))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            self.update_menu(prs_info)
        finally:
            self.refresh_lock.release()
            self.menu.get(REFRESH).title = REFRESH
            self.enable_refresh_button()

    def update_menu(self, prs_info):
        has_urgent_pr = False
        sorted_repos = sorted(prs_info.keys())
        for repo in sorted_repos:
            prs = prs_info[repo]
            if len(prs) == 0:
                continue
            has_red_prs = any(pr['status'] == '🔴' for pr in prs)
            has_orange_prs = any(pr['status'] in '💬' for pr in prs)
            has_yellow_prs = any(pr['status'] in '🟡' for pr in prs)
            has_green_prs = any(pr['status'] in '🟢' for pr in prs)

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
            sorted_prs = sorted(prs, key=lambda pr: pr['number'])
            for pr in sorted_prs:
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

    def process_repo(self, repo, prs_info):
        repo_name = repo['name']
        owner = repo['owner']['login']
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
        except FileNotFoundError:
            return {}

    def save_config(self, config):
        config_path = self.get_config_path()
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file)

    def request_github_token(self):
        root = tk.Tk()
        root.withdraw()
        token = simpledialog.askstring("GitHub Token", "Please enter your GitHub PAT:", show='*')
        root.destroy()
        return token.strip()

    def get_github_token(self):
        if not self.github_token:
            self.github_token = keyring.get_password('github', 'token')
        return self.github_token

    def set_github_pat_token(self, token: str) -> None:
        keyring.set_password('github', 'token', token)

    def get_headers(self) -> dict:
        return {'Authorization': f'token {self.get_github_token()}'}

    def get_all_repositories(self, filter_keyword: str = None) -> list:
        filter_keyword = filter_keyword.lower() if filter_keyword else None
        repos, page = [], 1

        try:
            while True:
                url = f'{API_GITHUB_BASE_URL}/user/repos?type=all&per_page=100&page={page}'
                response = requests.get(url, headers=self.get_headers())
                response.raise_for_status()
                page_repos = response.json()
                if not page_repos:
                    break
                if filter_keyword:
                    page_repos = [repo for repo in page_repos if filter_keyword in repo['name'].lower()]
                repos.extend(page_repos)
                page += 1
        except HTTPError as e:
            self.handle_http_error(f'Failed to fetch repositories', e)
        return repos

    def get_current_user_login(self) -> str:
        user_url = f'{API_GITHUB_BASE_URL}/user'
        try:
            response = requests.get(user_url, headers=self.get_headers())
            response.raise_for_status()
            return response.json().get('login', '')
        except HTTPError as e:
            self.handle_http_error('Failed to fetch current GitHub user', e)
            return ''

    def get_branch_protection_info(self, owner: str, repo: str, branch: str) -> dict:
        url = f'{API_GITHUB_BASE_URL}/repos/{owner}/{repo}/branches/{branch}/protection'
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            protection_info = response.json()
            required_reviewers = protection_info.get('required_pull_request_reviews', {}).get(
                'required_approving_review_count', 0)
            return {'required_reviewers': required_reviewers}
        except HTTPError as e:
            self.handle_http_error(f'Failed to fetch branch protection information for {branch}', e)
            return {'required_reviewers': 0}

    def get_pull_requests_for_repo(self, owner: str, repo: str) -> list:
        try:
            url = f'{API_GITHUB_BASE_URL}/repos/{owner}/{repo}/pulls'
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.handle_http_error(f'Failed to fetch pull requests list from repository: {repo}', e)
        return []

    def handle_http_error(self, custom_error_message: str, e: HTTPError) -> None:
        if e.response.status_code == http.HTTPStatus.UNAUTHORIZED:
            logging.warning(f'HTTP Warning: {custom_error_message} -> {e}')
            self.ask_for_github_pat_token()
        else:
            logging.error(f'HTTP Error: {custom_error_message} -> {e}')

    def get_pr_reviewers_info(self, owner: str, repo: str, pr_number: int, base_branch: str) -> dict:
        reviews_url = f'{API_GITHUB_BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews'
        requested_reviewers_url = f'{API_GITHUB_BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers'
        try:
            reviews_response = requests.get(reviews_url, headers=self.get_headers())
            reviews_response.raise_for_status()
            requested_reviewers_response = requests.get(requested_reviewers_url, headers=self.get_headers())
            requested_reviewers_response.raise_for_status()
            reviews = reviews_response.json()
            requested_reviewers = requested_reviewers_response.json()

            current_user = self.get_current_user_login()
            has_current_user_reviewed = any(review['user']['login'] == current_user for review in reviews)
            has_current_user_requested = any(
                review['user']['login'] == current_user for review in reviews if review['state'] == 'CHANGES_REQUESTED')
            review_statuses = {review['user']['login']: review['state'] for review in reviews}
            number_of_reviews = len(set(review_statuses.keys()))
            number_of_completed_reviews = len(
                set([review['user']['login'] for review in reviews if review['state'] == 'APPROVED']))
            branch_protection_info = self.get_branch_protection_info(owner, repo, base_branch)
            number_of_requested_reviewers = len(requested_reviewers.get('users', []))
            number_of_requested_reviewers = max(number_of_requested_reviewers,
                                                branch_protection_info['required_reviewers'])

            return {
                'number_of_reviews': number_of_reviews,
                'number_of_completed_reviews': number_of_completed_reviews,
                'number_of_requested_reviewers': number_of_requested_reviewers,
                'has_current_user_reviewed': has_current_user_reviewed,
                'has_current_user_requested': has_current_user_requested
            }
        except HTTPError as e:
            self.handle_http_error(f'Failed to fetch PR reviewers information for repository {repo}', e)
            return {}

    def format_pr_info(self, owner: str, pr: dict) -> dict:
        pr_title = pr['title']
        pr_url = pr['html_url']
        is_draft = pr['draft']
        pr_number = pr['number']
        base_branch = pr['base']['ref']
        reviewers_info = self.get_pr_reviewers_info(owner, pr['head']['repo']['name'], pr_number, base_branch)

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
