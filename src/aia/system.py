from __future__ import annotations

import shutil
import subprocess

from .errors import AiaError


def available_vram_bytes() -> int:
    if not shutil.which("nvidia-smi"):
        raise AiaError("NVIDIA tools unavailable. Install the NVIDIA driver.")
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.total,memory.used",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AiaError("Cannot read GPU memory. Run nvidia-smi to diagnose.")
    available = []
    try:
        for line in result.stdout.splitlines():
            total, used = (int(part.strip()) for part in line.split(",", 1))
            available.append(max(total - used, 0) * 1024 * 1024)
    except ValueError as error:
        raise AiaError("Cannot read GPU memory. Run nvidia-smi to diagnose.") from error
    if not available:
        raise AiaError("No NVIDIA GPU found.")
    return sum(available)


def restart_ollama() -> bool:
    result = subprocess.run(
        ["sudo", "systemctl", "restart", "ollama"], check=False
    )
    return result.returncode == 0
