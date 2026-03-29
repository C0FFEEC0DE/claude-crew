#!/usr/bin/env bash
set -euo pipefail

: "${PROMPT:?PROMPT is required}"
: "${CLAUDE_MODEL:?CLAUDE_MODEL is required}"
: "${MAX_TURNS:=8}"

set +e
claude -p "$PROMPT" \
  --model "$CLAUDE_MODEL" \
  --max-turns "$MAX_TURNS" \
  --output-format json \
  > claude-result.json 2> claude-stderr.log
status=$?
set -e

if [ ! -s claude-result.json ]; then
  echo "Claude output JSON is missing or empty" >&2
  status=1
elif ! jq -e '.' claude-result.json >/dev/null 2>&1; then
  echo "Claude output JSON is invalid" >&2
  status=1
else
  jq -r '.result // empty' claude-result.json > claude-result.txt
  if [ ! -s claude-result.txt ] || [ -z "$(tr -d '[:space:]' < claude-result.txt)" ]; then
    echo "Claude result text is missing or empty" >&2
    status=1
  fi
fi

if [ -s claude-stderr.log ]; then
  tail -n 200 claude-stderr.log > claude-stderr-tail.txt || true
fi

exit "$status"
