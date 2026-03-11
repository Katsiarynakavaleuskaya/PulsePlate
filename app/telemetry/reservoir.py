"""Hourly quota for bounded full-payload capture."""

from __future__ import annotations

import threading
import time
from typing import Callable


class HourlyReservoir:
    """Fixed-size per-hour capture quota with deterministic reset boundaries."""

    def __init__(
        self,
        n: int = 60,
        *,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.n = max(1, int(n))
        self.left = self.n
        self._time_fn = time_fn
        self.window = int(self._time_fn() // 3600)
        self.lock = threading.Lock()

    def take(self) -> bool:
        """Consume one quota slot if available in the current hour."""

        with self.lock:
            current_window = int(self._time_fn() // 3600)
            if current_window > self.window:
                self.window = current_window
                self.left = self.n
            if self.left <= 0:
                return False
            self.left -= 1
            return True
