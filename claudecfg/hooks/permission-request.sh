#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

command="$(json_get '.tool_input.command' | tr '[:upper:]' '[:lower:]')"

if [[ "$command" == *"npm publish"* || "$command" == *"cargo publish"* || "$command" == *"docker push"* || "$command" == *"gh release"* || "$command" == *"kubectl apply"* || "$command" == *"helm upgrade"* ]]; then
    jq -n '{
        hookSpecificOutput: {
            hookEventName: "PermissionRequest",
            decision: {
                behavior: "deny",
                message: "release/deploy requests are outside this profile"
            }
        }
    }'
    exit 0
fi

if [[ "$command" == *"curl "* && "$command" == *"| sh"* ]]; then
    jq -n '{
        hookSpecificOutput: {
            hookEventName: "PermissionRequest",
            decision: {
                behavior: "deny",
                message: "remote shell bootstrap commands require manual review outside the hook flow"
            }
        }
    }'
    exit 0
fi
