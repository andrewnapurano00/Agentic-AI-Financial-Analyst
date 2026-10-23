"""Per-build advisor pacing; count logical requests, not shared transport retries."""
from threading import Event, Lock

BATCH_SIZE = 100
PAUSE_SECONDS = 30
REQUEST_TIMEOUT = (3, 30)  # connect/read bounds; not a whole-build deadline


class CollectionStopped(RuntimeError):
    status_code = 429


class RequestBatch:
    def __init__(self, wait=None):
        self.stopped = Event()
        self._lock = Lock()
        self._wait = wait or self.stopped.wait
        self._count = 0
        self.pauses = 0

    @property
    def warning(self):
        return "FMP HTTP 429: collection stopped after rate limiting; successful evidence retained. Wait for the provider limit to reset, then explicitly refresh and Build again."

    def reserve(self, slots=1):
        if not 1 <= slots <= BATCH_SIZE:
            raise ValueError("Invalid advisor request batch reservation.")
        # Lock includes cooldown so all workers share the same hundred-request gate.
        with self._lock:
            if self.stopped.is_set():
                raise CollectionStopped(self.warning)
            if self._count+slots > BATCH_SIZE:
                self.pauses += 1
                self._wait(PAUSE_SECONDS)
                self._count = 0
                if self.stopped.is_set():
                    raise CollectionStopped(self.warning)
            self._count += slots

    def request(self, request, *args, **kwargs):
        self.reserve()
        if self.stopped.is_set():
            raise CollectionStopped(self.warning)
        kwargs["timeout"] = REQUEST_TIMEOUT
        try:
            return request(*args, **kwargs)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 429:
                self.stopped.set()
            raise
