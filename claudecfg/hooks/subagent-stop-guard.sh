#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

last_message="$(json_get '.last_assistant_message')"

if [ -z "$last_message" ]; then
    jq -n '{
        decision: "block",
        reason: "No assistant summary message was found for this subagent stop event."
    }'
    exit 0
fi

if ! message_mentions_concrete_outcome "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Subagent output must include a concrete outcome."
    }'
    exit 0
fi

if ! message_mentions_changed_files "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Subagent output must name changed files or explicitly say no files changed."
    }'
    exit 0
fi

if ! message_mentions_verification_status "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Subagent output must mention verification status or explicitly say verification was not run."
    }'
    exit 0
fi

if ! message_mentions_remaining_risks "$last_message" && ! message_mentions_next_step "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Subagent output must state remaining risks or the next step."
    }'
    exit 0
fi
