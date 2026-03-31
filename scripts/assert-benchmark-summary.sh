#!/bin/bash

set -euo pipefail

[ $# -eq 1 ] || {
    echo "Usage: $0 SUMMARY_JSON" >&2
    exit 1
}

summary_file="$1"
max_recovered_tasks="${BENCH_MAX_RECOVERED_TASKS:-0}"
max_summary_repaired="${BENCH_MAX_SUMMARY_REPAIRED_TASKS:-0}"

jq -e '
    .totals.configured_tasks > 0
    and .totals.executed_tasks > 0
    and .totals.executed_tasks <= .totals.configured_tasks
    and .totals.tasks == .totals.executed_tasks
    and .totals.passed == .totals.tasks
    and .totals.tool_failures == 0
    and .totals.policy_violations == 0
    and .totals.recovered_tasks <= $max_recovered_tasks
    and .totals.summary_repaired <= $max_summary_repaired
' --argjson max_recovered_tasks "$max_recovered_tasks" --argjson max_summary_repaired "$max_summary_repaired" "$summary_file" >/dev/null
