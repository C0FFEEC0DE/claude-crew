#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

payload="$(jq -n \
    --arg ts "$(timestamp_utc)" \
    --arg session_id "$(json_get '.session_id')" \
    --arg file_path "$(json_get '.file_path')" \
    --arg memory_type "$(json_get '.memory_type')" \
    --arg load_reason "$(json_get '.load_reason')" \
    '{
        ts: $ts,
        session_id: $session_id,
        file_path: $file_path,
        memory_type: $memory_type,
        load_reason: $load_reason
    }')"

append_jsonl "instructions-loaded.jsonl" "$payload"
