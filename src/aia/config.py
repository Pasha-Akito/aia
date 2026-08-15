from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        self.path = path or base / "aia" / "config.json"

    def get_default(self) -> str | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        value = data.get("default_model")
        return value if isinstance(value, str) and value else None

    def set_default(self, model: str) -> None:
        self._write({"default_model": model})

    def clear_default(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def _write(self, data: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix="config.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
                handle.write("\n")
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
