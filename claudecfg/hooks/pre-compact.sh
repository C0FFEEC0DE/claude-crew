#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

payload="$(jq -n \
    --arg ts "$(timestamp_utc)" \
    --arg session_id "$(json_get '.session_id')" \
    --arg trigger "$(json_get '.trigger')" \
    --slurpfile state "$(state_file)" \
    '{
        ts: $ts,
        session_id: $session_id,
        trigger: $trigger,
        state: $state[0]
    }')"

append_jsonl "pre-compact.jsonl" "$payload"
