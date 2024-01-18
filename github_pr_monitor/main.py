import argparse
import logging

from github_pr_monitor.app.github_pull_request_monitor_app import GithubPullRequestMonitorApp

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch GitHub PRs for repositories matching a keyword.")
    parser.add_argument("-r", "--repo_search_filter", help="Keyword to filter repositories", type=str)
    parser.add_argument("-p", "--pat", help="Set GitHub Personal Access Token", action="store_true")
    args = parser.parse_args()

    app = GithubPullRequestMonitorApp(repo_search_filter=args.repo_search_filter, ask_pat=args.pat)
    app.run()
