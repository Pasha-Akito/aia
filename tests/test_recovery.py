from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from aia.cli import recover_unload


class RecoveryClient:
    def __init__(self, unloads: bool, running: list[dict[str, str]] | None = None) -> None:
        self.unloads = unloads
        self.running = running or []
        self.logger = logging.getLogger("test.recovery")
        self.logger.addHandler(logging.NullHandler())

    def unload_and_verify(self, model: str) -> bool:
        return self.unloads

    def running_models(self):
        return self.running


class RecoveryTests(unittest.TestCase):
    @patch("aia.cli.restart_ollama", return_value=True)
    def test_restart_recovers_failed_normal_unload(self, restart) -> None:
        self.assertTrue(recover_unload(RecoveryClient(False), "model"))
        restart.assert_called_once_with()

    @patch("aia.cli.restart_ollama", return_value=True)
    def test_model_remaining_after_restart_is_failure(self, _restart) -> None:
        client = RecoveryClient(False, [{"name": "model"}])
        self.assertFalse(recover_unload(client, "model"))

    @patch("aia.cli.restart_ollama")
    def test_successful_normal_unload_does_not_restart(self, restart) -> None:
        self.assertTrue(recover_unload(RecoveryClient(True), "model"))
        restart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
