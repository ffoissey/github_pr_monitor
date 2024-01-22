import logging
import os

APPLICATION_MAX_THREADS = os.cpu_count() or 1
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
