from PyQt5.QtCore import QThread


class GlobalThreadPool:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._active = []
        self._queue = []

    def set_max_workers(self, n: int):
        self.max_workers = max(1, int(n))

    def submit(self, thread: QThread):
        thread.finished.connect(lambda: self._on_thread_finished(thread))
        if len(self._active) < self.max_workers:
            self._active.append(thread)
            thread.start()
        else:
            self._queue.append(thread)

    def _on_thread_finished(self, thread: QThread):
        try:
            self._active.remove(thread)
        except ValueError:
            pass
        if self._queue:
            next_thread = self._queue.pop(0)
            self._active.append(next_thread)
            next_thread.start()

    def active_count(self) -> int:
        return len(self._active)


global_thread_pool = GlobalThreadPool()
