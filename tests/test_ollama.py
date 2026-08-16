from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
import time
import unittest

from aia.ollama import OllamaClient


class FakeOllamaHandler(BaseHTTPRequestHandler):
    installed = [{"name": "tiny:latest", "size": 1000}]
    running = [{"name": "tiny:latest"}]
    requests: list[tuple[str, str, dict]] = []
    pull_delay = 0.0

    def log_message(self, *_args) -> None:
        pass

    def _payload(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.requests.append(("GET", self.path, {}))
        if self.path == "/api/tags":
            self._json({"models": self.installed})
        elif self.path == "/api/ps":
            self._json({"models": self.running})
        else:
            self._json({"error": "missing"}, 404)

    def do_POST(self) -> None:
        payload = self._payload()
        self.requests.append(("POST", self.path, payload))
        if self.path == "/api/pull":
            time.sleep(type(self).pull_delay)
        if self.path == "/api/generate" and payload.get("prompt"):
            body = b'{"response":"hello ","done":false}\n{"response":"world","done":true}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/generate":
            type(self).running = []
        self._json({"status": "success"})

    def do_DELETE(self) -> None:
        payload = self._payload()
        self.requests.append(("DELETE", self.path, payload))
        type(self).installed = [
            item for item in self.installed if item["name"] != payload.get("model")
        ]
        self._json({})


class OllamaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllamaHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.client = OllamaClient(f"http://{host}:{port}/api")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        FakeOllamaHandler.installed = [{"name": "tiny:latest", "size": 1000}]
        FakeOllamaHandler.running = [{"name": "tiny:latest"}]
        FakeOllamaHandler.requests = []
        FakeOllamaHandler.pull_delay = 0.0

    def test_list_generate_unload_delete_lifecycle(self) -> None:
        self.assertEqual(self.client.installed_models()[0]["name"], "tiny:latest")
        self.assertEqual("".join(self.client.generate("tiny:latest", "question")), "hello world")
        self.assertTrue(self.client.unload_and_verify("tiny:latest", delay=0))
        self.client.delete("tiny:latest")
        self.assertEqual(self.client.installed_models(), [])
        methods = [request[0] for request in FakeOllamaHandler.requests]
        self.assertIn("DELETE", methods)

    def test_pull_uses_non_streaming_api(self) -> None:
        self.client.pull("tiny:latest")
        self.assertIn(
            ("POST", "/api/pull", {"model": "tiny:latest", "stream": False}),
            FakeOllamaHandler.requests,
        )

    def test_pull_is_not_limited_by_normal_request_timeout(self) -> None:
        host, port = self.server.server_address
        client = OllamaClient(f"http://{host}:{port}/api", timeout=0.01)
        FakeOllamaHandler.pull_delay = 0.05
        client.pull("tiny:latest")

    def test_unload_retries_are_bounded(self) -> None:
        attempts = 0

        def unload(_model: str) -> None:
            nonlocal attempts
            attempts += 1

        self.client.request_unload = unload  # type: ignore[method-assign]
        self.client.running_models = lambda: [{"name": "tiny:latest"}]  # type: ignore[method-assign]
        try:
            self.assertFalse(
                self.client.unload_and_verify("tiny:latest", attempts=3, delay=0)
            )
            self.assertEqual(attempts, 3)
        finally:
            del self.client.request_unload
            del self.client.running_models


if __name__ == "__main__":
    unittest.main()
