#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

code_changed="$(jq -r '.code_changed // false' "$(state_file)")"
tests_ok="$(jq -r '.tests_ok' "$(state_file)")"

if [ "$code_changed" = "true" ] && [ "$tests_ok" != "true" ]; then
    echo "Task cannot be completed yet: code or config changed, but no successful test command was recorded for this session." >&2
    exit 2
fi
