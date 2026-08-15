from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from aia.config import ConfigStore


class ConfigTests(unittest.TestCase):
    def test_round_trip_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "config.json"
            store = ConfigStore(path)
            self.assertIsNone(store.get_default())
            store.set_default("gemma3:4b")
            self.assertEqual(store.get_default(), "gemma3:4b")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            store.clear_default()
            self.assertIsNone(store.get_default())

    def test_invalid_config_is_unconfigured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("not-json", encoding="utf-8")
            self.assertIsNone(ConfigStore(path).get_default())


if __name__ == "__main__":
    unittest.main()
