import json
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ai_lines import AILines
from local_llm import LocalLLM, Result
from predictor import NgramPredictor


class FakeWorker:
    def __init__(self):
        self.jobs, self.results = [], []

    def submit(self, *args):
        self.jobs.append(args)
        return True

    def poll(self):
        return self.results.pop(0) if self.results else None

    def close(self):
        pass


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.worker = FakeWorker()
        self.runner = AILines(2, NgramPredictor(Path(self.directory.name) / "model.json"),
                              self.worker, fallback_ms=500)
        self.runner.set_human("I remember the rain")

    def test_deadline_and_recovery_after_random_output(self):
        self.runner.on_user_keyed(0)
        due = self.runner.lines[0].due[0]
        self.runner.tick(due + 499)
        self.assertEqual(self.runner.lines[0].text, "")
        self.runner.tick(due + 500)
        self.assertEqual(len(self.runner.lines[0].text), 1)
        self.worker.results.append(Result(0, 0, 0, "Rain fell softly.", 800))
        self.runner.tick(2000)
        self.assertIn("Rain fell softly.", self.runner.lines[0].buffer)

    def test_edit_rejects_inflight_result(self):
        self.runner.on_user_keyed(0)
        self.runner.tick(0)
        self.runner.set_human("Changed", edited=True)
        self.worker.results.append(Result(0, 0, 0, "obsolete", 10))
        self.runner.tick(1)
        self.assertEqual(self.runner.lines[0].buffer, "")
        self.assertEqual(self.runner.stats["stale"], 1)

    def test_reset_rejects_inflight_result(self):
        self.runner.on_user_keyed(0)
        self.runner.tick(0)
        self.runner.reset()
        self.worker.results.append(Result(0, 0, 0, "obsolete", 10))
        self.runner.tick(2000)
        self.assertTrue(all(not line.text and not line.buffer for line in self.runner.lines))

    def test_refill_preserves_unconsumed_text(self):
        self.runner.lines[0].buffer = "old words"
        self.worker.results.append(Result(0, 0, 0, "New sentence.", 10))
        self.runner.tick(0)
        self.assertEqual(self.runner.lines[0].buffer, "old words New sentence.")

    def test_queues_bounded_and_requests_fair(self):
        for index in range(500):
            self.runner.on_user_keyed(index)
        self.assertTrue(all(len(line.due) == 24 for line in self.runner.lines))
        self.runner.tick(0)
        self.assertEqual(self.worker.jobs[-1][1], 0)
        self.worker.results.append(Result(0, 0, 0, "Some generated text.", 1))
        self.runner.tick(1)
        self.assertEqual(self.worker.jobs[-1][1], 1)

    def test_server_error_backs_off(self):
        self.worker.results.append(Result(0, 0, 0, "", 1, "offline"))
        self.runner.tick(0)
        self.assertEqual(self.runner.lines[0].retry_at, 3000)
        self.assertEqual(self.runner.stats["errors"], 1)


    def test_fast_typing_without_model_keeps_pace(self):
        self.runner.fallback_ms = 0
        next_key = 0
        for now in range(0, 3000, 16):
            if now >= next_key and next_key < 2000:
                self.runner.on_user_keyed(next_key)
                next_key += 50
            self.runner.tick(now)
        for line in self.runner.lines:
            self.assertEqual(len(line.text), 40)
            self.assertFalse(line.due)

    def test_fallback_wait_is_not_repeated_for_every_character(self):
        line = self.runner.lines[0]
        self.runner.on_user_keyed(0)
        due = line.due[0]
        self.runner.tick(due + 500)
        before = len(line.text)
        self.runner.on_user_keyed(due + 501)
        self.runner.tick(line.due[0])
        self.assertEqual(len(line.text), before + 1)

    def test_slow_model_recovers_after_many_fallback_characters(self):
        self.runner.fallback_ms = 0
        for now in range(0, 2000, 50):
            self.runner.on_user_keyed(now)
            self.runner.tick(now + 90)
        self.assertGreater(self.runner.stats["random_chars"], 50)
        self.worker.results.append(Result(0, 0, 0, "New AI sentence.", 2000))
        self.runner.tick(2100)
        self.runner.on_user_keyed(2200)
        self.runner.tick(2300)
        self.assertGreater(self.runner.stats["ai_chars"], 0)
        self.assertEqual(self.runner.stats["stale"], 0)

    def test_server_failures_back_off_globally(self):
        self.runner.on_user_keyed(0)
        self.runner.tick(0)
        self.worker.results.append(Result(0, 0, 0, "", 1, "offline"))
        self.runner.tick(1)
        self.runner.tick(999)
        self.assertEqual(len(self.worker.jobs), 1)
        self.runner.tick(1001)
        self.assertEqual(len(self.worker.jobs), 2)
        self.worker.results.append(Result(0, 1, 0, "", 1, "offline"))
        self.runner.tick(1002)
        self.runner.tick(3001)
        self.assertEqual(len(self.worker.jobs), 2)
        self.runner.tick(3002)
        self.assertEqual(len(self.worker.jobs), 3)

    def test_default_fallback_latency_at_40_keys_per_second(self):
        runner = AILines(9, self.runner.predictor, self.worker)
        typed = emitted = 0
        key_times = []
        next_key = 0
        for now in range(0, 2200, 8):
            if now >= next_key and next_key < 2000:
                runner.on_user_keyed(next_key)
                key_times.append(next_key)
                typed += 1
                next_key += 25
            runner.tick(now)
            count = runner.stats["random_chars"] // 9
            while emitted < count:
                self.assertLessEqual(now - key_times[emitted], 100)
                emitted += 1
        self.assertEqual(typed, 80)
        self.assertEqual(emitted, typed)
        self.assertTrue(all(not line.due for line in runner.lines))


class ClientTests(unittest.TestCase):
    def test_rejects_external_endpoints(self):
        with self.assertRaises(ValueError):
            LocalLLM("https://example.com/v1/chat/completions")

    def test_actual_http_protocol_and_error(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.server.payload = body
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"choices": [{"message": {"content": "Rain fell.\nQuiet streets."}}]}).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = LocalLLM(f"http://127.0.0.1:{server.server_port}/v1/chat/completions")
        try:
            self.assertTrue(client.submit(2, 1, 4, "human", "previous"))
            deadline, result = time.monotonic() + 3, None
            while result is None and time.monotonic() < deadline:
                result = client.poll()
                time.sleep(.01)
            self.assertIsNotNone(result)
            self.assertEqual(result.text, "Rain fell. Quiet streets.")
            self.assertEqual((result.epoch, result.row, result.revision), (2, 1, 4))
            self.assertFalse(server.payload["stream"])
        finally:
            client.close()
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()

