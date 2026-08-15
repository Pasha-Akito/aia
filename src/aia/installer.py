from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipapp

from .errors import AiaError


PLAN = """Install: ollama-cuda (if missing)
Enable: ollama.service
Install: /usr/local/bin/aia
Requires sudo."""


def confirm(input_fn: Callable[[str], str] = input) -> bool:
    while True:
        try:
            answer = input_fn("Continue? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            return False


def first_time_setup(
    *,
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> int:
    output(PLAN)
    if not confirm(input_fn):
        return 0
    if not shutil.which("pacman"):
        raise AiaError("Unsupported system. AIA currently requires Arch Linux.")
    if not shutil.which("nvidia-smi"):
        raise AiaError("NVIDIA tools unavailable. Install the NVIDIA driver first.")

    commands: list[list[str]] = []
    if not shutil.which("ollama"):
        commands.append(["sudo", "pacman", "-S", "--needed", "ollama-cuda"])
    commands.extend(
        [
            ["sudo", "systemctl", "enable", "--now", "ollama"],
        ]
    )
    for command in commands:
        result = run(command, text=True, check=False)
        if result.returncode != 0:
            raise AiaError(f"Setup failed. Check: {' '.join(command)}")

    source = Path(__file__).resolve().parents[1]
    if (source / "__main__.py").is_file():
        with tempfile.TemporaryDirectory(prefix="aia-install-") as temporary:
            archive = Path(temporary) / "aia.pyz"
            zipapp.create_archive(source, archive, interpreter="/usr/bin/env python3")
            result = run(
                ["sudo", "install", "-m", "0755", str(archive), "/usr/local/bin/aia"],
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise AiaError("Setup failed. Could not install /usr/local/bin/aia.")

    checks = [
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        ["systemctl", "is-active", "ollama"],
        ["/usr/local/bin/aia", "help"],
    ]
    for command in checks:
        result = run(command, stdout=subprocess.DEVNULL, text=True, check=False)
        if result.returncode != 0:
            raise AiaError(f"Verification failed. Check: {' '.join(command)}")
    output("Setup complete.")
    return 0
