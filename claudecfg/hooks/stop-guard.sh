#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

code_changed="$(jq -r '.code_changed // false' "$(state_file)")"
last_message="$(json_get '.last_assistant_message')"

if reason="$(session_block_reason)"; then
    jq -n --arg reason "$reason" '{
        decision: "block",
        reason: $reason
    }'
    exit 0
fi

if [ "$code_changed" = "true" ] && [ -z "$last_message" ]; then
    jq -n '{
        decision: "block",
        reason: "Code or config changed, but no assistant summary message was found for this stop event."
    }'
    exit 0
fi

if [ "$code_changed" = "true" ] && ! message_mentions_verification_status "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Final response must mention verification status after code or config changes."
    }'
    exit 0
fi

if [ "$code_changed" = "true" ] && ! message_mentions_review_outcome "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Final response must mention review outcome or explicitly say review is pending after code or config changes."
    }'
    exit 0
fi

if [ "$code_changed" = "true" ] && ! message_mentions_changed_files "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Final response must name key changed files or explicitly say no files changed."
    }'
    exit 0
fi

if [ "$code_changed" = "true" ] && ! message_mentions_remaining_risks "$last_message"; then
    jq -n '{
        decision: "block",
        reason: "Final response must state remaining risks or explicitly mark them as none."
    }'
    exit 0
fi
