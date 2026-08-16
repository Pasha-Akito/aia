from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Thread
import unittest
import zipapp


class LifecycleHandler(BaseHTTPRequestHandler):
    installed: list[dict[str, object]] = []
    running: list[dict[str, object]] = []

    def log_message(self, *_args) -> None:
        pass

    def _payload(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _send(self, payload: object, content_type: str = "application/json") -> None:
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/library":
            self._send(b'<a href="/library/tiny">tiny</a>', "text/html")
        elif self.path == "/library/tiny/tags":
            self._send(b'<a href="/library/tiny:1b">tiny:1b</a>', "text/html")
        elif self.path == "/v2/library/tiny/manifests/1b":
            self._send({"layers": [{"size": 1024**3}]})
        elif self.path == "/api/tags":
            self._send({"models": type(self).installed})
        elif self.path == "/api/ps":
            self._send({"models": type(self).running})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        payload = self._payload()
        if self.path == "/api/pull":
            model = payload["model"]
            type(self).installed = [{"name": model, "size": 1024**3}]
            self._send(
                b'{"status":"downloading","completed":50,"total":100}\n'
                b'{"status":"success"}\n',
                "application/x-ndjson",
            )
        elif self.path == "/api/generate" and payload.get("prompt"):
            type(self).running = [{"name": payload["model"]}]
            self._send(
                b'{"response":"It works.","done":true}\n',
                "application/x-ndjson",
            )
        elif self.path == "/api/generate":
            type(self).running = []
            self._send({"done": True})
        else:
            self.send_error(404)

    def do_DELETE(self) -> None:
        model = self._payload()["model"]
        type(self).installed = [item for item in type(self).installed if item["name"] != model]
        self._send({})


class InstalledExecutableEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LifecycleHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        LifecycleHandler.installed = []
        LifecycleHandler.running = []
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(__file__).resolve().parents[1]
        self.executable = Path(self.temporary.name) / "aia"
        zipapp.create_archive(root / "src", self.executable, interpreter="/usr/bin/env python3")
        self.executable.chmod(0o755)
        fake_bin = Path(self.temporary.name) / "bin"
        fake_bin.mkdir()
        nvidia_smi = fake_bin / "nvidia-smi"
        nvidia_smi.write_text("#!/bin/sh\nprintf '8192, 0\\n'\n", encoding="utf-8")
        nvidia_smi.chmod(0o755)
        host, port = self.server.server_address
        self.env = os.environ.copy()
        self.env.update(
            {
                "PATH": f"{fake_bin}:{self.env['PATH']}",
                "XDG_CONFIG_HOME": f"{self.temporary.name}/config",
                "XDG_STATE_HOME": f"{self.temporary.name}/state",
                "OLLAMA_HOST": f"http://{host}:{port}",
                "AIA_LIBRARY_URL": f"http://{host}:{port}/library",
                "AIA_TAGS_URL": f"http://{host}:{port}/library",
                "AIA_REGISTRY_URL": f"http://{host}:{port}/v2/library",
            }
        )

    def run_aia(self, *args: str, input_text: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.executable), *args],
            input=input_text,
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

    def test_download_use_delete_and_download_again(self) -> None:
        first_setup = self.run_aia("setup", input_text="1\n")
        self.assertEqual(first_setup.returncode, 0, first_setup.stderr)
        self.assertIn(
            "Retrieving models...\nSelect a model to install:\n1. tiny:1b",
            first_setup.stdout,
        )
        self.assertIn("Downloading tiny:1b:  50%", first_setup.stdout)
        self.assertIn("Downloading tiny:1b: 100%", first_setup.stdout)

        prompt = self.run_aia("What", "does", "ls", "do?")
        self.assertEqual(prompt.returncode, 0, prompt.stderr)
        self.assertEqual(prompt.stdout, "It works.\nModel unloaded.\n")
        self.assertEqual(LifecycleHandler.running, [])

        deletion = self.run_aia("delete", input_text="1\n")
        self.assertEqual(deletion.returncode, 0, deletion.stderr)
        self.assertIn("Delete installed models:\n1. tiny:1b", deletion.stdout)
        self.assertEqual(LifecycleHandler.installed, [])

        second_setup = self.run_aia("setup", input_text="1\n")
        self.assertEqual(second_setup.returncode, 0, second_setup.stderr)
        self.assertEqual(LifecycleHandler.installed[0]["name"], "tiny:1b")

    def test_help_commands_are_reachable_and_setup_can_cancel(self) -> None:
        help_result = self.run_aia("help")
        self.assertEqual(help_result.returncode, 0)
        for command in ("help", "first-time-setup", "setup", "config", "delete", "unload"):
            self.assertIn(f"aia {command}", help_result.stdout)
        cancelled = self.run_aia("first-time-setup", input_text="n\n")
        self.assertEqual(cancelled.returncode, 0)
        self.assertEqual(
            cancelled.stdout,
            "Install: ollama-cuda (if missing)\n"
            "Enable: ollama.service\n"
            "Install: /usr/local/bin/aia\n"
            "Requires sudo.\n"
            "Continue? [y/N] ",
        )


if __name__ == "__main__":
    unittest.main()
