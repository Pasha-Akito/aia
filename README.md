# Ollama Assistant

Ollama Assistant (`aia`) is a small command-line tool for asking a local Ollama model a single troubleshooting question. It streams the answer, unloads the model, and exits. It does not keep chat history or run its own background service.

## Supported platform

The initial target is Arch Linux with an NVIDIA GPU. Ollama provides model execution through its system service; the shell starts AIA only when an `aia` command is entered.

## Commands

```text
aia first-time-setup
aia setup
aia config
aia delete
aia unload
aia <message>
```

- `aia first-time-setup` explains and installs missing dependencies, configures Ollama, and installs the `aia` executable. It shows privileged operations before invoking `sudo` interactively.
- `aia setup` detects currently available VRAM and offers up to nine popular, uninstalled Ollama models expected to fit fully in it.
- `aia config` selects the default from locally installed Ollama models.
- `aia delete` deletes a selected locally installed Ollama model.
- `aia <message>` treats all remaining arguments as one prompt, so quotation marks are not required.
- `aia unload` retries model unloading and applies the same recovery used after a prompt.

The interactive model menus number choices `1` through `9` and reserve `0` for exiting without making a change. Installed-model menus use additional pages when needed so every installed model remains available.

## Runtime behavior

AIA loads the configured model through Ollama, streams its response, and always attempts to unload it before exiting. If normal unloading fails, AIA performs bounded automatic recovery, verifies the result, and reports any remaining manual action clearly.

Operational diagnostics are written to a per-user log file. Warnings and errors also appear in the terminal, and `--verbose` displays detailed diagnostics. Prompts and model responses are not logged by default.

## Installation and removal

`aia first-time-setup` is the supported installation path. Before changing the system, it must explain the dependencies and privileged commands it will use. Removal instructions must identify every AIA-owned file and must not remove user-installed Ollama models without explicit confirmation.

## Project documents

- [`SPEC.md`](SPEC.md) defines required behavior and acceptance criteria.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) records durable product and architecture decisions.
