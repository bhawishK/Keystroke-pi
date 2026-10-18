"""Bounded background client for a loopback llama.cpp chat server."""
from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, build_opener, ProxyHandler


@dataclass(frozen=True)
class Result:
    epoch: int
    row: int
    revision: int
    text: str
    elapsed_ms: float
    error: str = ""


class LocalLLM:
    def __init__(self, endpoint="http://127.0.0.1:8080/v1/chat/completions",
                 model="local", timeout=12.0):
        parsed = urlparse(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("LLM endpoint must be an HTTP loopback address")
        self.endpoint, self.model, self.timeout = endpoint, model, timeout
        self.requests = queue.Queue(maxsize=1)
        self.results = queue.Queue(maxsize=2)
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, name="local-llm", daemon=True)
        self.thread.start()

    def submit(self, epoch, row, revision, human, own):
        try:
            self.requests.put_nowait((epoch, row, revision, human[-320:], own[-160:]))
            return True
        except queue.Full:
            return False

    def poll(self):
        try:
            return self.results.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=0.2)

    def _run(self):
        # Bypass environment proxies: typed text goes only to the local server.
        opener = build_opener(ProxyHandler({}))
        while not self.stopped.is_set():
            try:
                epoch, row, revision, human, own = self.requests.get(timeout=0.1)
            except queue.Empty:
                continue
            started = time.monotonic()
            text, error = "", ""
            try:
                payload = {
                    "model": self.model, "stream": False, "max_tokens": 40,
                    "temperature": 0.85, "top_p": 0.9,
                    "messages": [{"role": "user", "content": (
                        "Write one short standalone sentence in a similar style to this text, "
                        "using different words. Do not copy the input. Output only the new sentence: " + human
                        + ("\nAvoid repeating this previous sentence: " + own if own else "")
                    )}],
                }
                request = Request(self.endpoint, data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"})
                with opener.open(request, timeout=self.timeout) as response:
                    data = json.loads(response.read(1024 * 1024))
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("Missing generated text")
                text = " ".join(content.split()).strip('"')[:240]
                if not text:
                    raise ValueError("Empty generated text")
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            result = Result(epoch, row, revision, text,
                            (time.monotonic() - started) * 1000, error)
            while not self.stopped.is_set():
                try:
                    self.results.put(result, timeout=0.1)
                    break
                except queue.Full:
                    pass
