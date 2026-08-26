"""Capped n-gram learner: next-character + inter-key timing."""

from __future__ import annotations

import json
import random
from pathlib import Path

from charset import random_cold_char

PREFIX_LEN = 3
SAVE_EVERY = 8
DEFAULT_INTERVAL_MS = 320
MAX_SAMPLES = 64
MAX_PREFIXES = 2000
MODEL_FILENAME = "model-v1.json"


class NgramPredictor:
    def __init__(self, path: Path, order: int = PREFIX_LEN) -> None:
        self.path = path
        self.order = order
        self.history: list[str] = []
        self.data: dict[str, dict[str, list]] = {"next": {}, "timing": {}}
        self.recency: list[str] = []
        self._keys_since_save = 0

    @property
    def prefix(self) -> str:
        if len(self.history) < self.order:
            return ""
        return "".join(self.history[-self.order :])

    def learn(self, char: str, interval_ms: float) -> None:
        prev = self.prefix
        if prev:
            self._touch_prefix(prev)
            next_bucket = self._bucket(self.data["next"], prev)
            next_bucket.append(char)
            if len(next_bucket) > MAX_SAMPLES:
                del next_bucket[: len(next_bucket) - MAX_SAMPLES]

            time_bucket = self._bucket(self.data["timing"], prev)
            time_bucket.append(_clamp(interval_ms, 40, 2000))
            if len(time_bucket) > MAX_SAMPLES:
                del time_bucket[: len(time_bucket) - MAX_SAMPLES]

        self.history.append(char)
        if len(self.history) > self.order + 8:
            self.history = self.history[-(self.order + 8) :]

        self._keys_since_save += 1
        if self._keys_since_save >= SAVE_EVERY:
            self.save()
            self._keys_since_save = 0

    def sample_char(self) -> str:
        local = self.data["next"].get(self.prefix) if self.prefix else None
        if local:
            return random.choice(local)
        uni = self._unigram_pool()
        if uni:
            return random.choice(uni)
        return random_cold_char()

    def predict_interval_ms(self) -> float:
        samples = self.data["timing"].get(self.prefix) if self.prefix else None
        if samples:
            return _median(samples)
        all_samples: list[float] = []
        for bucket in self.data["timing"].values():
            all_samples.extend(bucket)
        if all_samples:
            return _median(all_samples)
        return DEFAULT_INTERVAL_MS

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "next": self.data["next"],
                "timing": self.data["timing"],
                "recency": self.recency,
            }
            self.path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass

    def load(self) -> bool:
        try:
            if not self.path.is_file():
                return False
            parsed = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict) or "next" not in parsed or "timing" not in parsed:
                return False
            self.data = {"next": parsed["next"], "timing": parsed["timing"]}
            recency = parsed.get("recency")
            if isinstance(recency, list):
                self.recency = [k for k in recency if isinstance(k, str)]
            else:
                self.recency = list(self.data["next"].keys())
            for key in self.data["next"]:
                if key not in self.recency:
                    self.recency.append(key)
            self._prune()
            return True
        except (OSError, json.JSONDecodeError, TypeError):
            return False

    def reset(self) -> None:
        self.history = []
        self.data = {"next": {}, "timing": {}}
        self.recency = []
        self._keys_since_save = 0
        try:
            if self.path.exists():
                self.path.unlink()
        except OSError:
            pass

    def _bucket(self, mapping: dict[str, list], prefix: str) -> list:
        if prefix not in mapping:
            mapping[prefix] = []
        return mapping[prefix]

    def _touch_prefix(self, prefix: str) -> None:
        if prefix in self.recency:
            self.recency.remove(prefix)
        self.recency.append(prefix)
        self._prune()

    def _prune(self) -> None:
        while len(self.recency) > MAX_PREFIXES:
            old = self.recency.pop(0)
            self.data["next"].pop(old, None)
            self.data["timing"].pop(old, None)

    def _unigram_pool(self) -> list[str]:
        pool: list[str] = []
        for bucket in self.data["next"].values():
            pool.extend(bucket)
        return pool


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, value))


def _median(values: list[float]) -> float:
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2
    return sorted_values[mid]
