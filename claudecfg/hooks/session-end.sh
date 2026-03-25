#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

payload="$(jq -n \
    --arg ts "$(timestamp_utc)" \
    --arg session_id "$(json_get '.session_id')" \
    --arg cwd "$(json_get '.cwd')" \
    --arg transcript_path "$(json_get '.transcript_path')" \
    --arg reason "$(json_get '.reason')" \
    --slurpfile state "$(state_file)" \
    '{
        ts: $ts,
        session_id: $session_id,
        cwd: $cwd,
        transcript_path: $transcript_path,
        reason: $reason,
        state: $state[0]
    }')"

append_jsonl "session-index.jsonl" "$payload"
