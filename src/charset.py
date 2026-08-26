"""CardKB letter mode without Fn / Sym: letters, digits, space."""

from __future__ import annotations

import random
import re

ALLOWED_RE = re.compile(r"^[a-zA-Z0-9 ]$")
COLD_CHARS = "abcdefghijklmnopqrstuvwxyz"


def is_allowed_char(key: str) -> bool:
    return len(key) == 1 and ALLOWED_RE.match(key) is not None


def random_cold_char() -> str:
    return random.choice(COLD_CHARS)
