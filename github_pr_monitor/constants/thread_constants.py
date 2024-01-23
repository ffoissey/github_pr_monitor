import os

# Add more thread than os can provide for blocking tasks (like http requests)
APPLICATION_MAX_THREADS: int = (os.cpu_count() or 1) * 4
