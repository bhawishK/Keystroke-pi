"""Change screen positions without changing line identities or writing state."""
import random


class RowLayout:
    def __init__(self, count, interval_ms=0, rng=None):
        if count < 2 or interval_ms < 0:
            raise ValueError("Need at least two rows and a nonnegative interval")
        self.count = count
        self.interval_ms = interval_ms
        self.rng = rng if rng is not None else random.Random()
        self.reset()

    def reset(self):
        self.rows = list(range(self.count))
        self.next_shuffle = None

    def start(self, now_ms):
        if self.interval_ms and self.next_shuffle is None:
            self.next_shuffle = now_ms + self.interval_ms

    def tick(self, now_ms):
        if self.next_shuffle is None or now_ms < self.next_shuffle:
            return False
        previous = self.rows[:]
        for _ in range(32):
            candidate = previous[:]
            self.rng.shuffle(candidate)
            if all(old != new for old, new in zip(previous, candidate)):
                self.rows = candidate
                break
        else:
            # Bounded work even with a pathological/injected random generator.
            offset = self.rng.randrange(1, self.count)
            self.rows = previous[offset:] + previous[:offset]
        self.next_shuffle = now_ms + self.interval_ms
        return True
