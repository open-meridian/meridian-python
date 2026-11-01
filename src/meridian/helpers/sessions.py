"""A long-running session's restarts, shared by every role (SDK 0.35;
spec/each-role-is-one-generated-class, section 4, rulings 1009 and 1017).

`Backoff` is the wait between one failure and the next try: the first wait
`first_s`, doubling to at most `most_s`, each within `jitter` of itself (a
fraction: 0.2 is up to a fifth either way) so a fleet of plugins restarting
together does not try again together; and back to `first_s` once the work
has run `steady_s` without failing. `meridian.run` restarts a role's `run()`
with one, as the `again` loop eight plugins copied did:

    backoff = Backoff(first_s=1, most_s=60, jitter=0.2, steady_s=60)
    while True:
        try:
            await work()
        except Exception:
            await asyncio.sleep(backoff.failed())
        else:
            backoff.steady()

The supervisor of a reconnecting session (`Supervisor`, `Link`,
`SessionState`) joins it here with 924's helpers (SDK 0.35, part B).
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

__all__ = ["Backoff"]


class Backoff:
    """The wait after each failure, doubling within its jitter, and reset
    once steady (see the module). `clock` (seconds, monotonic) and `rng`
    are for a test, a behaviour case's fake clock and seed."""

    def __init__(
        self,
        first_s: float = 1.0,
        most_s: float = 60.0,
        jitter: float = 0.2,
        steady_s: float = 60.0,
        *,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        if first_s <= 0 or most_s < first_s:
            raise ValueError(f"first_s is above 0 and at most most_s: {first_s}, {most_s}")
        if not 0 <= jitter < 1:
            raise ValueError(f"jitter is a fraction from 0 to below 1: {jitter}")
        if steady_s < 0:
            raise ValueError(f"steady_s is 0 or more: {steady_s}")
        self.first_s = first_s
        self.most_s = most_s
        self.jitter = jitter
        self.steady_s = steady_s
        self._clock = clock
        self._rng = rng or random.Random()
        self._next = first_s
        self._since: float | None = None

    def failed(self) -> float:
        """The work failed: how long to wait before trying again. A failure
        after `steady_s` of steady running starts from `first_s` again."""
        now = self._clock()
        if self._since is not None and now - self._since >= self.steady_s:
            self._next = self.first_s
        base = self._next
        self._next = min(self._next * 2, self.most_s)
        self._since = now
        spread = base * self.jitter
        return base + self._rng.uniform(-spread, spread)

    def steady(self) -> None:
        """The work is running: once it has run `steady_s` since the last
        failure, the next failure waits `first_s` again."""
        if self._since is None or self._clock() - self._since >= self.steady_s:
            self._next = self.first_s
            self._since = None
