"""Process-local FMP transport budgets, never a distributed user quota."""
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
import secrets
import threading
import time


class ProviderLimited(RuntimeError):
    pass


@dataclass
class Bucket:
    starts: deque = field(default_factory=deque)
    active: int = 0
    failures: int = 0
    opened: float | None = None
    probe: bool = False
    last: float = 0


class ProviderLimits:
    def __init__(self, *, clock=time.monotonic, per_minute=300, concurrent=8,
                 global_concurrent=64, failures=5, cooldown=30, capacity=4096):
        self.clock = clock
        self.per_minute = per_minute
        self.concurrent = concurrent
        self.global_concurrent = global_concurrent
        self.failures = failures
        self.cooldown = cooldown
        self.capacity = capacity
        self._salt = secrets.token_bytes(32)
        self._buckets = {}
        self._active = 0
        self._lock = threading.Lock()

    @contextmanager
    def request(self, credential):
        scope = hmac.new(self._salt, credential.encode(), hashlib.sha256).digest()
        with self._lock:
            now = self.clock()
            if scope not in self._buckets:
                self._buckets = {k: b for k, b in self._buckets.items() if b.active or now-b.last < 3600}
                if len(self._buckets) >= self.capacity:
                    raise ProviderLimited("FMP local guard capacity reached; retry later.")
                self._buckets[scope] = Bucket(last=now)
            bucket = self._buckets[scope]
            bucket.last = now
            while bucket.starts and now-bucket.starts[0] >= 60:
                bucket.starts.popleft()
            if bucket.opened is not None:
                if now-bucket.opened < self.cooldown or bucket.probe:
                    raise ProviderLimited("FMP circuit open after transient failures; saved results remain available. Retry later.")
            if len(bucket.starts) >= self.per_minute:
                raise ProviderLimited("FMP local credential request quota reached; retry later.")
            if bucket.active >= self.concurrent or self._active >= self.global_concurrent:
                raise ProviderLimited("FMP local concurrency limit reached; retry later.")
            is_probe = bucket.opened is not None
            bucket.probe = is_probe
            bucket.active += 1
            self._active += 1
            bucket.starts.append(now)
        outcome = {"transient_failure": False}
        try:
            yield outcome
        finally:
            with self._lock:
                bucket.active -= 1
                self._active -= 1
                if outcome["transient_failure"]:
                    bucket.failures += 1
                    if is_probe or bucket.failures >= self.failures:
                        bucket.opened = self.clock()
                elif is_probe or bucket.opened is None:
                    bucket.failures = 0
                    bucket.opened = None
                if is_probe:
                    bucket.probe = False


FMP_LIMITS = ProviderLimits()
