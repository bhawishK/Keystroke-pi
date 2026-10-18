import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from row_layout import RowLayout


class RowLayoutTests(unittest.TestCase):
    def test_starts_on_first_key_and_moves_every_identity(self):
        layout = RowLayout(10, 3000, random.Random(4))
        self.assertFalse(layout.tick(9000))
        layout.start(9000)
        self.assertFalse(layout.tick(11999))
        for now in range(12000, 312000, 3000):
            previous = layout.rows[:]
            self.assertTrue(layout.tick(now))
            self.assertEqual(sorted(layout.rows), list(range(10)))
            self.assertTrue(all(a != b for a, b in zip(previous, layout.rows)))

    def test_disabled_reset_and_late_frame(self):
        disabled = RowLayout(10)
        disabled.start(0)
        self.assertFalse(disabled.tick(10000))
        layout = RowLayout(10, 3000, random.Random(1))
        layout.start(0)
        self.assertTrue(layout.tick(60000))
        self.assertFalse(layout.tick(60000))
        layout.reset()
        self.assertEqual(layout.rows, list(range(10)))
        self.assertFalse(layout.tick(90000))

    def test_typing_and_backspace_stay_with_human_after_shuffle(self):
        import pygame
        import main
        pygame.init()
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(
                main, "MODEL_PATH", Path(directory) / "model.json"
            ):
                app = main.KeystrokeApp(fullscreen=False, shuffle_ms=100)
                for char in "human":
                    app._on_typed(char, 0)
                for index, line in enumerate(app.ghosts.ghosts):
                    line.text = f"other {index}"
                old_position = app.row_layout.rows.index(app.live_index)
                self.assertTrue(app.row_layout.tick(100))
                new_position = app.row_layout.rows.index(app.live_index)
                self.assertNotEqual(old_position, new_position)
                self.assertEqual(app._line_text(app.row_layout.rows[new_position]), "human")
                app._on_typed("s", 101)
                app._on_backspace(102)
                self.assertEqual(app.live_text, "human")
                self.assertEqual([line.text for line in app.ghosts.ghosts],
                                 [f"other {index}" for index in range(9)])
                app._draw(102)
                app._reset()
                self.assertEqual(app.row_layout.rows, list(range(10)))
                self.assertIsNone(app.row_layout.next_shuffle)
        finally:
            pygame.quit()
