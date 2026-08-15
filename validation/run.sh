#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
validation_tmp="$(mktemp -d)"
trap 'rm -rf "$validation_tmp"' EXIT

export PYTHONPATH="$project_root/src"
export XDG_CONFIG_HOME="$validation_tmp/config"
export XDG_STATE_HOME="$validation_tmp/state"

python -m compileall -q "$project_root/src" "$project_root/tests" "$project_root/bin/aia"
python -m unittest discover -s "$project_root/tests" -v
python -m zipapp "$project_root/src" -o "$validation_tmp/aia" -p "/usr/bin/env python3"
chmod +x "$validation_tmp/aia"
"$validation_tmp/aia" help

set +e
empty_output="$("$validation_tmp/aia" 2>&1)"
empty_status=$?
set -e
test "$empty_status" -ne 0
test "$empty_output" = "Specify a command or message. Run: aia help"

git -C "$project_root" diff --check
