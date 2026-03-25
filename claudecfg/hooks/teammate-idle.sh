#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

code_changed="$(jq -r '.code_changed // false' "$(state_file)")"
tests_ok="$(jq -r '.tests_ok' "$(state_file)")"

if [ "$code_changed" = "true" ] && [ "$tests_ok" != "true" ]; then
    echo "Do not go idle yet: verification is still missing for this session." >&2
    exit 2
fi
