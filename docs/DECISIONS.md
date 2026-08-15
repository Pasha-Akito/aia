# Decision record

This file records durable product and architecture choices. It does not track implementation progress; Git history and pull requests provide that record.

## Single-turn CLI

AIA handles one question per invocation and stores no conversation history. Long-form conversation belongs in a dedicated chat product.

## Shell-launched process

The shell launches the `aia` executable directly. AIA runs only for the command and has no background service of its own. Ollama's service owns model execution.

## Initial platform

The first supported environment is Arch Linux with an NVIDIA GPU. A narrower platform target keeps installation, GPU detection, and end-to-end validation deterministic.

## First-time installation

`aia first-time-setup` may invoke `sudo` interactively to install dependencies and configure Ollama. It must explain privileged operations before executing them, favoring a simple installation flow without hiding system changes.

## Model discovery

`aia setup` uses the current popularity ordering from the Ollama model library rather than maintaining an AIA-owned catalogue. It excludes installed models and variants that are not expected to fit entirely within total VRAM minus current usage.

## Prompt interface

All arguments after `aia` form one prompt unless the first argument is a recognized subcommand. Users do not need quotation marks. Responses stream to the terminal.

## Configuration

Configuration is per user. `aia config` selects from all locally installed Ollama models. A missing configured model produces a clear recovery message; AIA does not silently replace or download it.

## Interactive model menus

The `setup`, `config`, and `delete` model menus show up to seven models at a time, numbered `1` through `7`. Selection `8` requests the previous page, `9` requests the next page, and `0` exits without downloading, changing, or deleting a model. Requesting a page that does not exist leaves the user on the current page. Setup is limited to three pages, while `config` and `delete` use as many pages as needed to list every installed model.

## Model deletion

`aia delete` removes a user-selected locally installed model through Ollama. Deleting the configured default clears that configuration and directs the user to `aia config` or `aia setup` before prompting.

## Model unloading

AIA always attempts immediate unloading, including after interruption or generation failure. It uses bounded retries, may restart Ollama when normal unloading fails, verifies the outcome, and exposes `aia unload` for manual recovery.

## Logging and privacy

Normal terminal output stays concise, while detailed operational diagnostics go to a per-user log and optionally the terminal with `--verbose`. Prompts and model responses are excluded from diagnostic logs by default.

## User-facing validation

Acceptance requires end-to-end scenarios through the installed CLI, not only unit-level evidence. Validation invokes every command advertised by help and follows a safe exit or completion path, exercises menu navigation, and verifies a real model can be downloaded, used, deleted, and downloaded again. Pull requests distinguish simulated integration coverage from validation performed with real Arch Linux, NVIDIA hardware, and Ollama.

## Product direction and implementation mechanics

Product intent and observable behavior are user-driven. Routine implementation details should be chosen autonomously to satisfy those outcomes with minimal user involvement, then refined through hands-on end-to-end feedback.
