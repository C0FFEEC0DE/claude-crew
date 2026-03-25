#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

payload="$(jq -n \
    --arg ts "$(timestamp_utc)" \
    --arg session_id "$(json_get '.session_id')" \
    --arg trigger "$(json_get '.trigger')" \
    --arg compact_summary "$(json_get '.compact_summary')" \
    '{
        ts: $ts,
        session_id: $session_id,
        trigger: $trigger,
        compact_summary: $compact_summary
    }')"

append_jsonl "post-compact.jsonl" "$payload"
