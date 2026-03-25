#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

emit_context "SubagentStart" "Subagent handoff contract: return outcome, changed files or 'no changes', verification status, and remaining risks or next step. If you edit code, run or request verification before stopping."
