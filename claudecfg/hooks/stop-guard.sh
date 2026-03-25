#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

code_changed="$(jq -r '.code_changed // false' "$(state_file)")"
tests_ok="$(jq -r '.tests_ok' "$(state_file)")"
last_message="$(json_get '.last_assistant_message')"

if [ "$code_changed" = "true" ] && [ "$tests_ok" != "true" ]; then
    jq -n '{
        decision: "block",
        reason: "Code or config changed, but no successful verification command was recorded in this session. Run tests before stopping."
    }'
    exit 0
fi

if [ "$code_changed" = "true" ] && ! grep -Eiq '(test|tests|pytest|coverage|lint|build|verified|verification|review|тест|проверк|ревью)' <<<"$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Final response must mention verification status after code or config changes."
    }'
    exit 0
fi
