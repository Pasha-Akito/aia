from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from datetime import datetime, timezone


def configure_logging(verbose: bool) -> tuple[logging.Logger, Path]:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    directory = base / "aia" / "logs"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = directory / f"aia-{stamp}-{os.getpid()}.log"

    logger = logging.getLogger("aia")
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if verbose:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger, path
