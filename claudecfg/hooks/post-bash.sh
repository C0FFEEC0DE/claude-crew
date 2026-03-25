#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

command="$(json_get '.tool_input.command')"
class="$(command_class "$command")"

case "$class" in
    test)
        tmp="$(mktemp)"
        jq \
            --arg command "$command" \
            '.tests_ok = true
            | .tests_failed = false
            | .last_test_command = $command' "$(state_file)" > "$tmp"
        mv "$tmp" "$(state_file)"
        emit_context "PostToolUse" "Successful verification command recorded: ${command}"
        ;;
    lint)
        tmp="$(mktemp)"
        jq \
            --arg command "$command" \
            '.lint_ok = true
            | .lint_failed = false
            | .last_lint_command = $command' "$(state_file)" > "$tmp"
        mv "$tmp" "$(state_file)"
        emit_context "PostToolUse" "Successful lint/static-check command recorded: ${command}"
        ;;
    build)
        tmp="$(mktemp)"
        jq \
            --arg command "$command" \
            '.build_ok = true
            | .build_failed = false
            | .last_build_command = $command' "$(state_file)" > "$tmp"
        mv "$tmp" "$(state_file)"
        emit_context "PostToolUse" "Successful build command recorded: ${command}"
        ;;
    *)
        exit 0
        ;;
esac
