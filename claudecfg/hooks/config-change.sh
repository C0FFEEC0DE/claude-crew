#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

payload="$(jq -n \
    --arg ts "$(timestamp_utc)" \
    --arg session_id "$(json_get '.session_id')" \
    --arg source "$(json_get '.source')" \
    --arg file_path "$(json_get '.file_path')" \
    '{
        ts: $ts,
        session_id: $session_id,
        source: $source,
        file_path: $file_path
    }')"

append_jsonl "config-change.jsonl" "$payload"
