from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from aia.installer import confirm, first_time_setup


class InstallerTests(unittest.TestCase):
    def test_confirmation_variants(self) -> None:
        self.assertTrue(confirm(lambda _: "YES"))
        self.assertTrue(confirm(lambda _: "y"))
        self.assertFalse(confirm(lambda _: "no"))
        self.assertFalse(confirm(lambda _: ""))

    def test_invalid_confirmation_reprompts(self) -> None:
        answers = iter(["maybe", "n"])
        self.assertFalse(confirm(lambda _: next(answers)))

    def test_decline_makes_no_system_calls(self) -> None:
        calls: list[list[str]] = []
        result = first_time_setup(
            input_fn=lambda _: "n",
            output=lambda _: None,
            run=lambda command, **_: calls.append(command),  # type: ignore[arg-type,return-value]
        )
        self.assertEqual(result, 0)
        self.assertEqual(calls, [])

    @patch("aia.installer.shutil.which")
    @patch("aia.installer.zipapp.create_archive")
    def test_confirm_runs_install_and_verification(self, archive, which) -> None:
        which.side_effect = lambda name: f"/usr/bin/{name}" if name != "ollama" else None
        calls: list[list[str]] = []

        def run(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)

        result = first_time_setup(input_fn=lambda _: "y", output=lambda _: None, run=run)
        self.assertEqual(result, 0)
        self.assertIn(["sudo", "pacman", "-S", "--needed", "ollama-cuda"], calls)
        self.assertIn(["sudo", "systemctl", "enable", "--now", "ollama"], calls)
        self.assertTrue(any(command[:3] == ["sudo", "install", "-m"] for command in calls))


if __name__ == "__main__":
    unittest.main()
