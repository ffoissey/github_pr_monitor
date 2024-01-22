import logging
import os

from github_pr_monitor.managers.thread_manager import ThreadManager

# Add more thread than os can provide for blocking tasks (like http requests)
APPLICATION_MAX_THREADS = (os.cpu_count() or 1) * 4
THREAD_MANAGER = ThreadManager(APPLICATION_MAX_THREADS)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
