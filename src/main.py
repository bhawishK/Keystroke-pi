"""Square native typing app for the cyberdeck keystroke spike."""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

import pygame

from charset import is_allowed_char
from ghosts import GhostRunner, trim_line, visible_tail
from predictor import MODEL_FILENAME, NgramPredictor

APP_SIZE = 720
LINE_COUNT = 10
RESET_HOLD_MS = 2000
CARET_PERIOD_MS = 1050
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "data" / MODEL_FILENAME
HINT_TEXT = "Type"

FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Cochin.ttc"),
    Path("/Library/Fonts/Cochin.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
    Path("/usr/share/fonts/truetype/freefont/FreeSerif.ttf"),
)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
HINT_COLOR = (89, 89, 89)


def is_raspberry_pi() -> bool:
    model_path = Path("/proc/device-tree/model")
    if not model_path.exists():
        return False
    try:
        return "raspberry" in model_path.read_text(errors="ignore").lower()
    except OSError:
        return False


def resolve_font_path() -> Path | None:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return path
    return None


def load_font(size: int) -> pygame.font.Font:
    path = resolve_font_path()
    if path is not None:
        try:
            return pygame.font.Font(str(path), size)
        except pygame.error:
            pass
    return pygame.font.SysFont("serif", size)


class KeystrokeApp:
    def __init__(self, *, fullscreen: bool) -> None:
        flags = pygame.SCALED
        if fullscreen:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((APP_SIZE, APP_SIZE), flags)
        pygame.display.set_caption("keystroke — spike")
        self.clock = pygame.time.Clock()
        self.font = load_font(int(APP_SIZE * 0.046))
        self.hint_font = load_font(int(APP_SIZE * 0.032))

        self.predictor = NgramPredictor(MODEL_PATH)
        self.predictor.load()
        self.live_index = random.randrange(LINE_COUNT)
        self.ghosts = GhostRunner(LINE_COUNT - 1, self.predictor)

        self.live_text = ""
        self.last_key_time: int | None = None
        self.backspace_down_at: int | None = None
        self.show_hint = True
        self.pad_x = int(APP_SIZE * 0.05)
        self.pad_y = int(APP_SIZE * 0.06)
        self.row_h = (APP_SIZE - self.pad_y * 2) / LINE_COUNT

    def run(self) -> None:
        running = True
        try:
            while running:
                now = pygame.time.get_ticks()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        running = self._on_key_down(event, now)
                    elif event.type == pygame.KEYUP:
                        if event.key == pygame.K_BACKSPACE:
                            self.backspace_down_at = None
                if not running:
                    break
                if self.backspace_down_at is not None and now - self.backspace_down_at >= RESET_HOLD_MS:
                    self._reset()
                    self.backspace_down_at = None
                self.ghosts.tick(now)
                self._draw(now)
                self.clock.tick(60)
        finally:
            self.predictor.save()

    def _on_key_down(self, event: pygame.event.Event, now: int) -> bool:
        if event.key == pygame.K_ESCAPE:
            return False
        mods = pygame.key.get_mods()
        if mods & (pygame.KMOD_CTRL | pygame.KMOD_META | pygame.KMOD_ALT):
            return True
        if event.key == pygame.K_BACKSPACE:
            if self.backspace_down_at is None:
                self.backspace_down_at = now
                self._on_backspace(now)
            return True
        self.backspace_down_at = None
        char = event.unicode or ""
        if is_allowed_char(char):
            self._on_typed(char, now)
        return True

    def _on_typed(self, char: str, now: int) -> None:
        self.show_hint = False
        interval = (
            now - self.last_key_time
            if self.last_key_time is not None
            else self.predictor.predict_interval_ms()
        )
        self.last_key_time = now
        self.live_text = trim_line(self.live_text + char)
        self.predictor.learn(char, interval)
        self.ghosts.on_user_keyed(now)

    def _on_backspace(self, now: int) -> None:
        self.show_hint = False
        if not self.live_text:
            return
        self.live_text = self.live_text[:-1]
        self.last_key_time = now

    def _reset(self) -> None:
        self.predictor.reset()
        self.ghosts.reset()
        self.live_text = ""
        self.last_key_time = None
        self.show_hint = True

    def _line_text(self, row: int) -> str:
        if row == self.live_index:
            return visible_tail(self.live_text)
        ghost_index = row if row < self.live_index else row - 1
        return self.ghosts.visible(ghost_index)

    def _draw(self, now: int) -> None:
        self.screen.fill(BLACK)
        if self.show_hint:
            hint = self.hint_font.render(HINT_TEXT, True, HINT_COLOR)
            hint_rect = hint.get_rect(centerx=APP_SIZE // 2, top=int(APP_SIZE * 0.014))
            self.screen.blit(hint, hint_rect)

        caret_on = (now // (CARET_PERIOD_MS // 2)) % 2 == 0
        caret_w = max(2, int(self.font.get_height() * 0.07))
        caret_h = int(self.font.get_height() * 0.92)

        for i in range(LINE_COUNT):
            text = self._line_text(i)
            surface = self.font.render(text, True, WHITE) if text else None
            y = self.pad_y + self.row_h * i + (self.row_h - self.font.get_height()) / 2
            x = self.pad_x
            if surface is not None:
                self.screen.blit(surface, (x, y))
                x += surface.get_width() + 2
            if caret_on:
                pygame.draw.rect(
                    self.screen,
                    WHITE,
                    pygame.Rect(int(x), int(y + self.font.get_height() * 0.08), caret_w, caret_h),
                )
        pygame.display.flip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ten-line keystroke learner for the cyberdeck.")
    display = parser.add_mutually_exclusive_group()
    display.add_argument(
        "--fullscreen",
        action="store_true",
        help="Fill the display (default on Raspberry Pi).",
    )
    display.add_argument(
        "--window",
        action="store_true",
        help="Use a fixed 720 × 720 window (default on Mac).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fullscreen = args.fullscreen or (is_raspberry_pi() and not args.window)
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    pygame.init()
    pygame.key.set_repeat(0)
    try:
        KeystrokeApp(fullscreen=fullscreen).run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"keystroke-spike-pi failed: {exc}", file=sys.stderr)
        raise
