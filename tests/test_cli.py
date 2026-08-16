from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aia.cli import COMMANDS, main, ollama_api_url
from aia.config import ConfigStore
from aia.discovery import Candidate
from aia.errors import AiaError


class FakeClient:
    def __init__(self) -> None:
        self.models = [
            {"name": f"model-{number}", "size": number * 1024**3}
            for number in range(1, 11)
        ]
        self.running: list[dict[str, object]] = []
        self.pulled: list[str] = []
        self.deleted: list[str] = []
        self.unloaded: list[str] = []
        self.pull_progress: list[int] = []
        self.logger = logging.getLogger("test.fake-client")

    def installed_models(self):
        return list(self.models)

    def running_models(self):
        return list(self.running)

    def pull(self, model, progress=None):
        self.pulled.append(model)
        if progress:
            for percentage in (25, 75, 100):
                progress(percentage)

    def delete(self, model):
        self.deleted.append(model)
        self.models = [item for item in self.models if item["name"] != model]

    def generate(self, model, prompt):
        yield "answer"

    def unload_and_verify(self, model):
        self.unloaded.append(model)
        return True


class FailingGenerationClient(FakeClient):
    failure: BaseException = AiaError("Generation failed.")

    def generate(self, model, prompt):
        raise self.failure
        yield  # pragma: no cover


class CliFunctionalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = patch.dict("os.environ", {"XDG_STATE_HOME": self.temporary.name})
        self.state.start()
        self.addCleanup(self.state.stop)
        self.store = ConfigStore(Path(self.temporary.name) / "config.json")
        self.client = FakeClient()
        self.output: list[str] = []
        self.errors: list[str] = []

    def invoke(self, args, inputs=()):
        entered = iter(inputs)
        return main(
            args,
            input_fn=lambda _: next(entered),
            output=self.output.append,
            error=self.errors.append,
            client=self.client,  # type: ignore[arg-type]
            store=self.store,
            progress=lambda _model, percentage: self.client.pull_progress.append(percentage),
        )

    def test_help_advertises_every_command(self) -> None:
        self.assertEqual(self.invoke(["help"]), 0)
        rendered = "\n".join(self.output)
        for command in COMMANDS:
            self.assertIn(f"aia {command}", rendered)
        self.assertIn("aia download         Select a model to install", rendered)

    def test_ollama_host_is_normalized(self) -> None:
        self.assertEqual(ollama_api_url("127.0.0.1:11434"), "http://127.0.0.1:11434/api")
        self.assertEqual(ollama_api_url("http://host/api"), "http://host/api")

    def test_empty_invocation_is_actionable_failure(self) -> None:
        self.assertEqual(self.invoke([]), 2)
        self.assertEqual(self.errors, ["Specify a command or message. Run: aia help"])

    def test_config_next_page_selects_default(self) -> None:
        self.assertEqual(self.invoke(["config"], ["9", "2"]), 0)
        self.assertEqual(self.store.get_default(), "model-9")
        self.assertEqual(self.output[0], "Select your default model:")

    def test_config_zero_does_not_change_default(self) -> None:
        self.store.set_default("model-1")
        self.assertEqual(self.invoke(["config"], ["0"]), 0)
        self.assertEqual(self.store.get_default(), "model-1")

    def test_delete_default_clears_configuration(self) -> None:
        self.store.set_default("model-1")
        self.assertEqual(self.invoke(["delete"], ["1"]), 0)
        self.assertEqual(self.client.deleted, ["model-1"])
        self.assertIsNone(self.store.get_default())
        self.assertIn("Default deleted. Run: aia config or aia download", self.output)

    @patch("aia.cli.available_vram_bytes", return_value=8 * 1024**3)
    @patch("aia.cli.LibraryClient")
    def test_download_downloads_and_configures_selection(self, library, _vram) -> None:
        library.return_value.candidates.return_value = [
            Candidate("tiny", 2 * 1024**3, 3 * 1024**3)
        ]
        self.assertEqual(self.invoke(["download"], ["1"]), 0)
        self.assertEqual(self.client.pulled, ["tiny"])
        self.assertEqual(self.store.get_default(), "tiny")
        self.assertEqual(self.output[0], "Retrieving models...")
        self.assertEqual(self.output[1], "Select a model to install:")
        self.assertEqual(self.client.pull_progress, [0, 25, 75, 100])

    def test_unquoted_message_streams_and_unloads(self) -> None:
        self.store.set_default("model-1")
        stream = StringIO()
        with redirect_stdout(stream):
            self.assertEqual(self.invoke(["What", "is", "ls?"]), 0)
        self.assertEqual(stream.getvalue(), "answer\n")
        self.assertEqual(self.client.unloaded, ["model-1"])

    def test_prompt_and_response_are_not_logged(self) -> None:
        self.store.set_default("model-1")
        with redirect_stdout(StringIO()):
            self.assertEqual(self.invoke(["private", "question"]), 0)
        logs = list((Path(self.temporary.name) / "aia" / "logs").glob("*.log"))
        content = logs[-1].read_text(encoding="utf-8")
        self.assertNotIn("private question", content)
        self.assertNotIn("answer", content)

    def test_generation_failure_still_unloads(self) -> None:
        client = FailingGenerationClient()
        self.client = client
        self.store.set_default("model-1")
        with redirect_stdout(StringIO()):
            self.assertEqual(self.invoke(["question"]), 1)
        self.assertEqual(client.unloaded, ["model-1"])
        self.assertEqual(self.errors, ["Generation failed."])

    def test_interruption_still_unloads(self) -> None:
        client = FailingGenerationClient()
        client.failure = KeyboardInterrupt()
        self.client = client
        self.store.set_default("model-1")
        with redirect_stdout(StringIO()):
            self.assertEqual(self.invoke(["question"]), 130)
        self.assertEqual(client.unloaded, ["model-1"])
        self.assertEqual(self.errors, ["Interrupted."])

    def test_missing_configured_model_is_reported_before_config_menu(self) -> None:
        self.store.set_default("removed")
        self.assertEqual(self.invoke(["config"], ["0"]), 0)
        self.assertEqual(self.output[:2], ["Default model missing.", "Select your default model:"])

    def test_every_help_command_has_a_safe_invocation(self) -> None:
        safe_inputs = {"setup": ["n"], "download": ["0"], "config": ["0"], "delete": ["0"]}
        for command in COMMANDS:
            with self.subTest(command=command):
                self.output.clear()
                self.errors.clear()
                if command == "download":
                    with patch("aia.cli.available_vram_bytes", return_value=8 * 1024**3), patch(
                        "aia.cli.LibraryClient"
                    ) as library:
                        library.return_value.candidates.return_value = [Candidate("tiny", 1, 1)]
                        status = self.invoke([command], safe_inputs[command])
                elif command == "unload":
                    status = self.invoke([command])
                else:
                    status = self.invoke([command], safe_inputs.get(command, []))
                self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
