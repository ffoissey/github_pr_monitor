import threading
import queue
from typing import Any, Callable


class ThreadManager:
    def __init__(self, max_threads: int):
        self.active_threads = []
        self.threads_lock = threading.Lock()
        self.thread_queue = queue.Queue(max_threads)

    def start_thread(self, target, args=(), daemon: bool = False) -> None:
        thread = threading.Thread(target=self._run_and_release, args=(target, args, daemon), daemon=daemon)
        if daemon is False:
            self.thread_queue.put(thread)
        thread.start()

    def _run_and_release(self, target: Callable, args: Any, daemon: bool = True) -> None:
        try:
            target(*args)
        finally:
            if daemon is False:
                self.thread_queue.get()
                self.thread_queue.task_done()

    def wait_for_all_threads(self) -> None:
        self.thread_queue.join()
