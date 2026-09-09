import threading
import time


class RequestPacer:
    """Global per-host rate limiter shared by every request in the app.

    Props: a minimum interval between any two requests to the same host
    (regardless of how many worker threads run), plus a cooldown triggered by
    HTTP 429 that makes every thread wait before hitting the server again,
    giving it time to recover. Best-effort: never raises on its own.
    """

    def __init__(self, min_interval=0.25, cooldown=20.0):
        self.min_interval = max(0.0, float(min_interval))
        self.cooldown = max(0.0, float(cooldown))
        self._lock = threading.Lock()
        self._last = {}
        self._hold = {}

    def wait(self, host):
        now = time.monotonic()
        with self._lock:
            target = max(now, self._last.get(host, 0.0) + self.min_interval, self._hold.get(host, 0.0))
            self._last[host] = target
            delay = max(0.0, target - now)
        if delay > 0:
            time.sleep(delay)

    def note_throttle(self, host):
        with self._lock:
            self._hold[host] = time.monotonic() + self.cooldown

    def throttled(self, host):
        with self._lock:
            return time.monotonic() < self._hold.get(host, 0.0)