import threading
import queue


class ThreadManager:
    def __init__(self, max_threads):
        self.active_threads = []
        self.max_threads = max_threads
        self.threads_lock = threading.Lock()
        self.thread_queue = queue.Queue(max_threads)

    def start_thread(self, target, args=()):
        thread = threading.Thread(target=self._run_and_release, args=(target, args))
        self.thread_queue.put(thread)
        thread.start()

    def _run_and_release(self, target, args):
        try:
            target(*args)
        finally:
            self.thread_queue.get()
            self.thread_queue.task_done()

    def wait_for_all_threads(self):
        self.thread_queue.join()
