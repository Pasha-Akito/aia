# Ollama Assistant

`aia` is a small, single-turn command-line assistant for quickly asking a local Ollama model troubleshooting questions. The shell launches the Python CLI for each command; AIA keeps no chat history, runs no background service of its own, and does not implement model serving.

AIA manages first-time installation, model discovery and selection, configuration, prompting, and reliable model unloading. Ollama handles model execution through its system service.

## Platform

- Arch Linux with an NVIDIA GPU is the initial supported platform.
- Installation is per machine and configuration is per user.

## Commands

### `aia help`

- List every available AIA command with enough information for the user to identify the appropriate command.

### `aia`

- When invoked without a command or message, return a clear error telling the user to specify a command and run `aia help` to see the available commands.
- Exit with a nonzero status.

### `aia first-time-setup`

- Explain which dependencies and privileged operations are required before making changes.
- Interactively invoke `sudo` when needed.
- Install Ollama and other required dependencies when absent.
- Enable and start the Ollama system service.
- Install the `aia` executable so it is available through the shell.
- Verify the NVIDIA tooling, Ollama service, and AIA installation.
- Document all installation and removal behavior in the README.

### `aia setup`

- Require a working first-time installation.
- Calculate available VRAM as total NVIDIA GPU VRAM minus current usage at setup time.
- Retrieve the current popularity ordering from the Ollama model library without maintaining an AIA-owned catalogue.
- Consider only local, general-purpose models with a downloadable variant expected to fit entirely in available VRAM; do not show partially fitting models.
- Exclude models already installed.
- Show up to nine eligible models, ordered by the Ollama library's popularity ranking, with useful selection details such as model name, download size, and estimated VRAM requirement.
- Number model choices `1` through `9`, with `0` reserved for exiting without downloading a model or changing the default.
- Download the selected model and make it the default.
- Return a clear, actionable error when model discovery is unavailable or no compatible models are found.

### `aia config`

- List all locally installed Ollama models and allow the user to select the default, using additional pages when more than nine are installed.
- Number the models on each page `1` through `9`, allow navigation between pages, and reserve `0` for exiting without changing the default.
- If no models are installed, tell the user to run `aia setup`.
- If the configured model was removed externally, report that clearly and require the user to choose or install another model.

### `aia delete`

- List all locally installed Ollama models and allow the user to select one to delete, using additional pages when more than nine are installed.
- Number the models on each page `1` through `9`, allow navigation between pages, and reserve `0` for exiting without deleting a model.
- Delete the selected model through Ollama.
- If the deleted model was the configured default, clear the default and tell the user to run `aia config` or `aia setup` before prompting.
- If no models are installed, report that there is nothing to delete.

### `aia <message>`

- Treat every argument after `aia` as one prompt unless the first argument is a recognized subcommand; quotation marks are not required.
- Require a configured, locally installed model.
- Load the configured model through Ollama, stream its response to the terminal, and exit after completion.
- Always attempt immediate model unloading, including after interruption or generation failure.
- If unloading fails, retry a bounded number of times with short delays, then restart the Ollama service and verify again.
- If AIA still cannot confirm unloading, print a prominent error with the manual recovery command.

### `aia unload`

- Attempt to unload running Ollama models and verify that they have left memory.
- Apply the same bounded retry and service-restart recovery used after prompts.
- Clearly report any model that remains loaded and provide an actionable manual recovery command.

## Logging and errors

- Show concise status, streamed answers, warnings, and actionable errors in the terminal.
- Write detailed operational diagnostics to a timestamped per-user log file.
- Mirror detailed diagnostics to the terminal when `--verbose` is used.
- Do not record prompts or model responses in diagnostic logs by default.
- Log model loading, unloading attempts, recovery actions, Ollama failures, and command outcomes.
- Return a nonzero exit status when an operation fails or model unloading cannot be confirmed.

## Product boundaries

- AIA is single-turn and stores no conversation history.
- AIA has no background service; the shell launches the CLI and Ollama provides model serving.
- AIA does not silently select a different model, install a model, or hide unloading failure.
- Routine recovery should minimize user input while keeping privileged or disruptive actions visible.

## Acceptance criteria

- `aia help` lists every available AIA command.
- Running `aia` without a command or message returns a nonzero exit status and tells the user to specify a command and use `aia help`.
- On supported Arch Linux and NVIDIA hardware, `aia first-time-setup` explains its changes, installs missing requirements with interactive privilege escalation, starts Ollama, installs AIA, and verifies the result.
- `aia setup` shows at most nine popular, uninstalled Ollama models expected to fit in currently available VRAM, numbers them `1` through `9`, reserves `0` for exit, and downloads and configures the selected model.
- `aia config` lists every locally installed model across pages of choices numbered `1` through `9`, reserves `0` for exit, changes the default when a model is selected, and subsequent questions use the new selection.
- `aia delete` lists every locally installed model across pages of choices numbered `1` through `9`, reserves `0` for exit, and deletes the selected model; deleting the configured default clears it and provides a recovery instruction.
- When no model is installed or the configured model is missing, AIA gives a clear recovery instruction.
- Given a configured model, `aia What does the ls command do?` streams an answer without requiring quotation marks.
- The command exits after returning the response and confirms that the model was unloaded.
- Interruptions and generation failures still trigger bounded unloading recovery.
- When normal unloading fails, AIA retries, restarts Ollama, verifies the result, and reports any remaining failure with an `aia unload` recovery path.
- Operational failures produce actionable terminal messages, detailed diagnostic logs, and nonzero exit statuses.
