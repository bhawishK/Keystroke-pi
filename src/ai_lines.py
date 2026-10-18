"""Main-thread line scheduler; the worker never touches Pygame or line state."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from collections import deque

from ghosts import trim_line, visible_tail


@dataclass
class Line:
    text: str = ""
    buffer: str = ""
    due: deque = field(default_factory=lambda: deque(maxlen=24))
    revision: int = 0
    retry_at: int = 0
    fallback_active: bool = False


class AILines:
    def __init__(self, count, predictor, worker, fallback_ms=0):
        self.predictor, self.worker = predictor, worker
        self.fallback_ms = fallback_ms
        self.lines = [Line() for _ in range(count)]
        self.human = ""
        self.epoch = 0
        self.pending = None
        self.cursor = 0
        self.active = False
        self.last_key_ms = None
        self.next_request_at = 0
        self.failures = 0
        self.stats = {"ai_chars": 0, "random_chars": 0, "stale": 0, "errors": 0,
                      "requests": 0, "last_latency_ms": 0, "fallback_entries": 0}
        self.last_error = ""

    def on_user_keyed(self, now_ms):
        self.active = True
        # The learned rhythm can be much slower than the current typing burst.
        # Schedule from actual arrival time, never accumulate predicted delays.
        interval = (now_ms - self.last_key_ms if self.last_key_ms is not None
                    else self.predictor.predict_interval_ms())
        self.last_key_ms = now_ms
        base = max(1, min(80, interval * 0.5))
        for line in self.lines:
            if len(line.due) < line.due.maxlen:
                due = now_ms + int(base * random.uniform(.72, 1.0))
                line.due.append(max(due, line.due[-1] if line.due else due))

    def set_human(self, text, edited=False):
        self.human = text
        if edited:
            self.epoch += 1
            for line in self.lines:
                line.buffer = ""

    def tick(self, now_ms):
        while (result := self.worker.poll()) is not None:
            self.pending = None
            line = self.lines[result.row]
            self.stats["last_latency_ms"] = round(result.elapsed_ms)
            if result.error:
                self.stats["errors"] += 1
                self.last_error = result.error
                self.failures += 1
                self.next_request_at = now_ms + min(30000, 1000 * 2 ** min(5, self.failures - 1))
                line.retry_at = now_ms + 3000
            elif result.epoch != self.epoch or result.revision != line.revision:
                self.stats["stale"] += 1
                line.retry_at = now_ms + 100
            else:
                preceding = line.buffer or line.text
                separator = " " if preceding and not preceding.endswith(" ") else ""
                line.buffer = (line.buffer + separator + result.text)[:256]
                self.last_error = ""
                self.failures = 0
                self.next_request_at = 0

        for line in self.lines:
            # Drain a bounded number of overdue keys each frame. No extra 70 ms
            # spacing: that imposed an absolute throughput ceiling on fast typing.
            emitted = 0
            while line.due and line.due[0] <= now_ms and emitted < 8:
                if line.buffer:
                    char, line.buffer = line.buffer[0], line.buffer[1:]
                    line.fallback_active = False
                    self.stats["ai_chars"] += 1
                elif line.fallback_active or now_ms - line.due[0] >= self.fallback_ms:
                    if not line.fallback_active:
                        self.stats["fallback_entries"] += 1
                    line.fallback_active = True
                    char = self.predictor.sample_char()
                    self.stats["random_chars"] += 1
                else:
                    break
                line.text = trim_line(line.text + char)
                line.due.popleft()
                emitted += 1

        if self.active and self.pending is None and now_ms >= self.next_request_at:
            for offset in range(len(self.lines)):
                index = (self.cursor + offset) % len(self.lines)
                line = self.lines[index]
                # Requests produce standalone passages rather than exact suffixes.
                # Fallback therefore need not invalidate a slow request; edits do.
                if len(line.buffer) < 32 and now_ms >= line.retry_at:
                    own = trim_line(line.text + line.buffer)
                    if self.worker.submit(self.epoch, index, line.revision, self.human, own):
                        self.pending = index
                        self.cursor = (index + 1) % len(self.lines)
                        self.stats["requests"] += 1
                    break

    def visible(self, index):
        return visible_tail(self.lines[index].text)

    def reset(self):
        self.epoch += 1
        self.lines = [Line() for _ in self.lines]
        self.human = ""
        self.active = False
        self.last_key_ms = None

    def close(self):
        self.worker.close()
