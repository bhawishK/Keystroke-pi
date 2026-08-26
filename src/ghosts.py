"""Nine shadow typists: one predicted character per user key, at predicted timing."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

MAX_LINE_CHARS = 160
VISIBLE_CHARS = 42


@dataclass
class Ghost:
    text: str = ""
    queue: list[tuple[int, str]] = field(default_factory=list)
    busy_until: int = 0


class GhostRunner:
    def __init__(self, count: int, predictor) -> None:
        self.predictor = predictor
        self.ghosts = [Ghost() for _ in range(count)]

    def on_user_keyed(self, now_ms: int) -> None:
        base = self.predictor.predict_interval_ms()
        for ghost in self.ghosts:
            wait = int(_jitter(base))
            start = max(now_ms, ghost.busy_until)
            due = start + wait
            ghost.queue.append((due, self.predictor.sample_char()))
            ghost.busy_until = due

    def tick(self, now_ms: int) -> None:
        for ghost in self.ghosts:
            remaining: list[tuple[int, str]] = []
            for due, char in ghost.queue:
                if due <= now_ms:
                    ghost.text = trim_line(ghost.text + char)
                else:
                    remaining.append((due, char))
            ghost.queue = remaining

    def reset(self) -> None:
        for ghost in self.ghosts:
            ghost.text = ""
            ghost.queue = []
            ghost.busy_until = 0

    def visible(self, index: int) -> str:
        return visible_tail(self.ghosts[index].text)


def trim_line(text: str) -> str:
    return text[-MAX_LINE_CHARS:] if len(text) > MAX_LINE_CHARS else text


def visible_tail(text: str) -> str:
    return text[-VISIBLE_CHARS:] if len(text) > VISIBLE_CHARS else text


def _jitter(base_ms: float) -> float:
    return min(1400, max(70, base_ms * (0.72 + random.random() * 0.56)))
