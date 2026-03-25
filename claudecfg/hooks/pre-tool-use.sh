#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

command="$(json_get '.tool_input.command' | tr '[:upper:]' '[:lower:]')"

if [[ "$command" =~ (^|[[:space:]])sudo[[:space:]] ]]; then
    emit_pretool_decision "deny" "sudo is blocked by the SDLC safety profile."
    exit 0
fi

if [[ "$command" =~ (^|[[:space:]])(mkfs|dd)[[:space:]] ]]; then
    emit_pretool_decision "deny" "Dangerous disk commands are blocked."
    exit 0
fi

if [[ "$command" == *"rm -rf /"* || "$command" == *"git reset --hard"* || "$command" == *"git push --force"* ]]; then
    emit_pretool_decision "deny" "Destructive commands are blocked by policy."
    exit 0
fi

if [[ "$command" == *"npm publish"* || "$command" == *"cargo publish"* || "$command" == *"docker push"* || "$command" == *"gh release"* || "$command" == *"kubectl apply"* || "$command" == *"helm upgrade"* ]]; then
    emit_pretool_decision "deny" "release/deploy actions are intentionally out of scope for this workflow profile."
    exit 0
fi

if [[ "$command" == *"curl "* && "$command" == *"| sh"* ]]; then
    emit_pretool_decision "deny" "Piping remote scripts into the shell is blocked."
    exit 0
fi
