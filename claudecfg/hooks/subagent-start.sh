#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

label="$(extract_subagent_label)"
tmp="$(mktemp)"
jq \
    --arg label "$label" \
    '.subagent_start_count = ((.subagent_start_count // 0) + 1)
    | .subagents_started = ((.subagents_started + (if ($label | length) > 0 then [$label] else [] end)) | unique)' "$(state_file)" > "$tmp"
mv "$tmp" "$(state_file)"

if [ -n "$label" ]; then
    emit_context "SubagentStart" "Recorded subagent handoff: @${label}. Return outcome, changed files or 'no changes', verification status, and remaining risks or next step. If you edit code, run or request verification before stopping."
else
    emit_context "SubagentStart" "Subagent handoff contract: return outcome, changed files or 'no changes', verification status, and remaining risks or next step. If you edit code, run or request verification before stopping."
fi
