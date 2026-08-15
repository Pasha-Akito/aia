from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from aia.system import available_vram_bytes


class SystemTests(unittest.TestCase):
    @patch("aia.system.shutil.which", return_value="/usr/bin/nvidia-smi")
    @patch("aia.system.subprocess.run")
    def test_available_vram_sums_all_gpus(self, run, _which) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="8192, 1024\n4096, 512\n")
        self.assertEqual(available_vram_bytes(), (7168 + 3584) * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
