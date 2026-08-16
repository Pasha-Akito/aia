from __future__ import annotations

from collections.abc import Callable, Sequence
import os
import sys
from typing import TextIO

from .config import ConfigStore
from .discovery import LibraryClient
from .errors import AiaError
from .installer import first_time_setup
from .logging import configure_logging
from .menu import select_paged
from .ollama import OllamaClient
from .system import available_vram_bytes, restart_ollama


COMMANDS = {
    "help": "Show commands",
    "setup": "Install AIA and Ollama",
    "download": "Select a model to install",
    "config": "Select the default model",
    "delete": "Delete an installed model",
    "unload": "Unload running models",
}


def ollama_api_url(value: str) -> str:
    host = value.rstrip("/")
    if "://" not in host:
        host = f"http://{host}"
    return host if host.endswith("/api") else f"{host}/api"


def help_command(output: Callable[[str], None]) -> int:
    for command, description in COMMANDS.items():
        output(f"aia {command:<16} {description}")
    output("aia <message>          Ask a question")
    return 0


def model_name(model: dict[str, object]) -> str:
    return str(model.get("name") or model.get("model") or "")


def format_installed(model: dict[str, object]) -> str:
    name = model_name(model)
    size = model.get("size")
    if isinstance(size, int):
        return f"{name} ({size / 1024**3:.1f} GB)"
    return name


def terminal_progress(model: str, percentage: int) -> None:
    sys.stdout.write(f"\rDownloading {model}: {percentage:3d}%")
    if percentage == 100:
        sys.stdout.write("\n")
    sys.stdout.flush()


def recover_unload(client: OllamaClient, model: str) -> bool:
    if client.unload_and_verify(model):
        return True
    client.logger.warning("Normal unload failed for %s; restarting Ollama", model)
    if restart_ollama():
        try:
            loaded = {model_name(item) for item in client.running_models()}
            if model not in loaded:
                return True
        except AiaError:
            pass
    return False


def download_command(
    client: OllamaClient,
    store: ConfigStore,
    *,
    input_fn: Callable[[str], str],
    output: Callable[[str], None],
    progress: Callable[[str, int], None],
) -> int:
    installed = {model_name(item) for item in client.installed_models()}
    output("Retrieving models...")
    candidates = LibraryClient().candidates(available_vram_bytes(), installed)
    selected = select_paged(
        "Select a model to install:",
        candidates,
        lambda item: item.display,
        input_fn=input_fn,
        output=output,
    )
    if selected is None:
        return 0
    progress(selected.name, 0)
    client.pull(selected.name, lambda percentage: progress(selected.name, percentage))
    store.set_default(selected.name)
    output(f"Default: {selected.name}")
    return 0


def config_command(
    client: OllamaClient,
    store: ConfigStore,
    *,
    input_fn: Callable[[str], str],
    output: Callable[[str], None],
) -> int:
    models = client.installed_models()
    if not models:
        raise AiaError("No models installed. Run: aia download")
    configured = store.get_default()
    installed = {model_name(model) for model in models}
    if configured and configured not in installed:
        output("Default model missing.")
    selected = select_paged(
        "Select your default model:", models, format_installed, input_fn=input_fn, output=output
    )
    if selected is not None:
        name = model_name(selected)
        store.set_default(name)
        output(f"Default: {name}")
    return 0


def delete_command(
    client: OllamaClient,
    store: ConfigStore,
    *,
    input_fn: Callable[[str], str],
    output: Callable[[str], None],
) -> int:
    models = client.installed_models()
    if not models:
        output("No installed models.")
        return 0
    selected = select_paged(
        "Delete installed models:", models, format_installed, input_fn=input_fn, output=output
    )
    if selected is None:
        return 0
    name = model_name(selected)
    client.delete(name)
    if store.get_default() == name:
        store.clear_default()
        output("Default deleted. Run: aia config or aia download")
    else:
        output(f"Deleted: {name}")
    return 0


def unload_command(client: OllamaClient, output: Callable[[str], None]) -> int:
    models = client.running_models()
    for item in models:
        name = model_name(item)
        if not recover_unload(client, name):
            raise AiaError(f"Model still loaded: {name}. Run: sudo systemctl restart ollama")
    if models:
        output("Models unloaded.")
    return 0


def prompt_command(
    message: str, client: OllamaClient, store: ConfigStore, output_stream: TextIO
) -> int:
    model = store.get_default()
    installed = {model_name(item) for item in client.installed_models()}
    if not model:
        raise AiaError("No default model. Run: aia download")
    if model not in installed:
        raise AiaError("Default model missing. Run: aia config or aia download")
    try:
        for text in client.generate(model, message):
            output_stream.write(text)
            output_stream.flush()
        output_stream.write("\n")
    except (AiaError, KeyboardInterrupt):
        raise
    finally:
        if not recover_unload(client, model):
            raise AiaError(f"Model still loaded: {model}. Run: aia unload")
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
    error: Callable[[str], None] | None = None,
    client: OllamaClient | None = None,
    store: ConfigStore | None = None,
    progress: Callable[[str, int], None] | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    verbose = False
    if "--verbose" in args:
        args.remove("--verbose")
        verbose = True
    error = error or (lambda text: print(text, file=sys.stderr))
    try:
        logger, _ = configure_logging(verbose)
    except OSError:
        error("Cannot write the AIA log. Check directory permissions.")
        return 1
    client = client or OllamaClient(
        ollama_api_url(os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")), logger
    )
    store = store or ConfigStore()
    progress = progress or terminal_progress
    if not args:
        error("Specify a command or message. Run: aia help")
        return 2
    command = args[0]
    logger.info("Command started: %s", command if command in COMMANDS else "prompt")
    try:
        if command == "help":
            result = help_command(output)
        elif command == "setup":
            result = first_time_setup(input_fn=input_fn, output=output)
        elif command == "download":
            result = download_command(
                client, store, input_fn=input_fn, output=output, progress=progress
            )
        elif command == "config":
            result = config_command(client, store, input_fn=input_fn, output=output)
        elif command == "delete":
            result = delete_command(client, store, input_fn=input_fn, output=output)
        elif command == "unload":
            result = unload_command(client, output)
        else:
            result = prompt_command(" ".join(args), client, store, sys.stdout)
        logger.info("Command completed: status=%d", result)
        return result
    except KeyboardInterrupt:
        error("Interrupted.")
        logger.warning("Command interrupted")
        return 130
    except AiaError as failure:
        error(str(failure))
        logger.error("Command failed: %s", failure)
        return 1
