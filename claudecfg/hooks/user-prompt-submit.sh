#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

ensure_state

prompt="$(json_get '.prompt' | tr '[:upper:]' '[:lower:]')"
task_type="other"

if grep -Eiq '(bug|fix|regression|defect|баг|ошиб|исправ)' <<<"$prompt"; then
    task_type="bugfix"
elif grep -Eiq '(refactor|rename|cleanup|tech debt|рефактор|почист|переимен)' <<<"$prompt"; then
    task_type="refactor"
elif grep -Eiq '(feature|implement|add support|integrat|new capability|фич|добав|интеграц|подключ|модел|pyrit|openrouter)' <<<"$prompt"; then
    task_type="feature"
elif grep -Eiq '(docs|readme|document|док|ридми)' <<<"$prompt"; then
    task_type="docs"
elif grep -Eiq '(review|audit|ревью|аудит|проверь)' <<<"$prompt"; then
    task_type="review"
fi

tmp="$(mktemp)"
jq --arg task_type "$task_type" '.task_type = $task_type' "$(state_file)" > "$tmp"
mv "$tmp" "$(state_file)"

case "$task_type" in
    feature)
        emit_context "UserPromptSubmit" "Treat this as a feature workflow. Before completion, ensure implementation is done, tests were executed successfully, review findings were addressed, and docs impact was handled when user-facing behavior changed. release/deploy remains out of scope."
        ;;
    bugfix)
        emit_context "UserPromptSubmit" "Treat this as a bugfix workflow. Reproduce or describe failure mode, implement the fix, execute regression tests, summarize verification, and finish with review plus docs update if behavior changed."
        ;;
    refactor)
        emit_context "UserPromptSubmit" "Treat this as a refactor workflow. Keep scope to structure and maintainability, preserve behavior, run verification after changes, and summarize risks plus changed files before stopping."
        ;;
    *)
        exit 0
        ;;
esac
