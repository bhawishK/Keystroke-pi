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


class AILines:
    def __init__(self, count, predictor, worker, fallback_ms=500):
        self.predictor, self.worker = predictor, worker
        self.fallback_ms = fallback_ms
        self.lines = [Line() for _ in range(count)]
        self.human = ""
        self.epoch = 0
        self.pending = None
        self.cursor = 0
        self.active = False
        self.stats = {"ai_chars": 0, "random_chars": 0, "stale": 0, "errors": 0,
                      "requests": 0, "last_latency_ms": 0}
        self.last_error = ""

    def on_user_keyed(self, now_ms):
        self.active = True
        base = self.predictor.predict_interval_ms()
        for line in self.lines:
            start = max(now_ms, line.due[-1] if line.due else now_ms)
            if len(line.due) < line.due.maxlen:
                line.due.append(start + int(max(70, min(1400, base * random.uniform(.72, 1.28)))))

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
                line.retry_at = now_ms + 3000
            elif result.epoch != self.epoch or result.revision != line.revision:
                self.stats["stale"] += 1
                line.retry_at = now_ms + 100
            else:
                preceding = line.buffer or line.text
                separator = " " if preceding and not preceding.endswith(" ") else ""
                line.buffer = (line.buffer + separator + result.text)[:256]
                self.last_error = ""

        for index, line in enumerate(self.lines):
            if not line.due or line.due[0] > now_ms:
                continue
            if line.buffer:
                char, line.buffer = line.buffer[0], line.buffer[1:]
                self.stats["ai_chars"] += 1
            elif now_ms - line.due[0] >= self.fallback_ms:
                char = self.predictor.sample_char()
                self.stats["random_chars"] += 1
            else:
                continue
            line.text = trim_line(line.text + char)
            line.due.popleft()
            # Space remaining queued characters from now; never dump a backlog.
            if line.due:
                shift = max(0, now_ms + 70 - line.due[0])
                line.due = deque((due + shift for due in line.due), maxlen=24)

        if self.active and self.pending is None:
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

    def close(self):
        self.worker.close()
