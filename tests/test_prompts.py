import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from writing_prompts import build_messages, clean_output
from local_llm import LocalLLM


class WritingPromptTests(unittest.TestCase):
    def test_nine_distinct_strategies_with_exact_samples(self):
        strategies = set()
        for row in range(9):
            messages = build_messages("desktop", row, "i walked home", "quiet streets")
            self.assertEqual(messages[0]["role"], "system")
            payload = json.loads(messages[1]["content"])
            self.assertEqual(payload["human_sample"], "i walked home")
            self.assertEqual(payload["your_previous_line"], "quiet streets")
            strategies.add(payload["strategy"])
        self.assertEqual(len(strategies), 9)

    def test_desktop_output_uses_same_keyboard_alphabet(self):
        self.assertEqual(clean_output('"i walked, slowly…\nthen home!"', "desktop"),
                         "i walked slowly then home")
        self.assertLessEqual(len(clean_output("x" * 1000, "desktop")), 240)

    def test_basic_prompt_and_punctuation_remain_available(self):
        self.assertEqual(len(build_messages("basic", 0, "human", "previous")), 1)
        self.assertEqual(clean_output("Rain fell.", "basic"), "Rain fell.")

    def test_unknown_profile_rejected_before_starting_thread(self):
        with self.assertRaises(ValueError):
            LocalLLM(profile="invalid")

    def test_desktop_has_longer_timeout_without_changing_basic(self):
        for profile, expected in [("basic", 12), ("desktop", 45)]:
            client = LocalLLM(profile=profile)
            try:
                self.assertEqual(client.timeout, expected)
            finally:
                client.close()


if __name__ == "__main__":
    unittest.main()
