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
- After presenting the plan, ask the user to confirm whether to continue before making any change or invoking `sudo`.
- Accept `yes` or `y` case-insensitively to continue and `no` or `n` to exit successfully without changing the system. Treat end-of-input or interruption at the confirmation as cancellation, and ask again after other input.
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
- Show up to three pages of seven eligible models, ordered by the Ollama library's popularity ranking, with useful selection details such as model name, download size, and estimated VRAM requirement.
- On each page, number model choices `1` through `7`, use `8` for the previous page, use `9` for the next page, and reserve `0` for exiting without downloading a model or changing the default.
- If the requested previous or next page does not exist, remain on the current page without changing anything.
- Download the selected model and make it the default.
- Return a clear, actionable error when model discovery is unavailable or no compatible models are found.

### `aia config`

- List all locally installed Ollama models and allow the user to select the default, using as many pages as necessary.
- On each page, number model choices `1` through `7`, use `8` for the previous page, use `9` for the next page, and reserve `0` for exiting without changing the default.
- If the requested previous or next page does not exist, remain on the current page without changing anything.
- If no models are installed, tell the user to run `aia setup`.
- If the configured model was removed externally, report that clearly and require the user to choose or install another model.

### `aia delete`

- List all locally installed Ollama models and allow the user to select one to delete, using as many pages as necessary.
- On each page, number model choices `1` through `7`, use `8` for the previous page, use `9` for the next page, and reserve `0` for exiting without deleting a model.
- If the requested previous or next page does not exist, remain on the current page without changing anything.
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

## End-to-end validation

- Treat user-visible end-to-end scenarios as required validation, in addition to lower-level automated tests.
- Exercise commands through the installed `aia` executable and their real user-facing prompts, output, exit statuses, configuration, Ollama operations, and recovery paths.
- Validate that every command shown by `aia help` can actually be invoked. Where completing a command would make an unwanted change, follow its normal exit or cancellation path and verify that it exits safely without changing state.
- Validate both first-time-setup confirmation paths: declining must exit without invoking `sudo` or changing the system, while confirming must proceed with the explained installation plan.
- Validate the complete model lifecycle by using `aia setup` to download and configure a model, prompting that model through `aia <message>`, deleting it through `aia delete`, and downloading it again through `aia setup`.
- Exercise menu navigation from a user's perspective, including model selection, exit with `0`, previous page with `8`, next page with `9`, and unavailable-page navigation that remains safely on the current page.
- Run supported-platform scenarios against a real Arch Linux, NVIDIA, and Ollama environment when they depend on actual system integration. Clearly distinguish real-system results from simulated integration results in the pull request.
- Record the scenarios performed, their observable results, and any environment limitation in the pull request so acceptance evidence can be reviewed before merge.

## Acceptance criteria

- `aia help` lists every available AIA command.
- Running `aia` without a command or message returns a nonzero exit status and tells the user to specify a command and use `aia help`.
- On supported Arch Linux and NVIDIA hardware, `aia first-time-setup` explains its changes and asks for confirmation before invoking `sudo` or changing the system; declining exits successfully without changes, while confirming installs missing requirements with interactive privilege escalation, starts Ollama, installs AIA, and verifies the result.
- `aia setup` shows at most three pages of seven popular, uninstalled Ollama models expected to fit in currently available VRAM; `1` through `7` select a model, `8` and `9` navigate, and `0` exits.
- `aia config` lists every locally installed model across as many seven-model pages as necessary; `1` through `7` select a model, `8` and `9` navigate, and `0` exits. A selection changes the default, and subsequent questions use it.
- `aia delete` lists every locally installed model across as many seven-model pages as necessary; `1` through `7` select a model, `8` and `9` navigate, and `0` exits. A selection deletes the model; deleting the configured default clears it and provides a recovery instruction.
- When no model is installed or the configured model is missing, AIA gives a clear recovery instruction.
- Given a configured model, `aia What does the ls command do?` streams an answer without requiring quotation marks.
- The command exits after returning the response and confirms that the model was unloaded.
- Interruptions and generation failures still trigger bounded unloading recovery.
- When normal unloading fails, AIA retries, restarts Ollama, verifies the result, and reports any remaining failure with an `aia unload` recovery path.
- Operational failures produce actionable terminal messages, detailed diagnostic logs, and nonzero exit statuses.
- End-to-end validation invokes every command advertised by `aia help` and safely exits or completes it through its user-facing interface.
- A real-system model lifecycle test downloads and configures a model, uses it for a prompt, deletes it, and downloads it again successfully.
