import logging

from github_pr_monitor.constants.thread_constants import APPLICATION_MAX_THREADS
from github_pr_monitor.managers.thread_manager import ThreadManager

THREAD_MANAGER = ThreadManager(APPLICATION_MAX_THREADS)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
