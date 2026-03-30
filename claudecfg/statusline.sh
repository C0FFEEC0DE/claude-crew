#!/bin/bash

set -euo pipefail

input="$(cat)"

color_reset="$(printf '\033[0m')"
color_dim="$(printf '\033[2m')"
color_red="$(printf '\033[31m')"
color_green="$(printf '\033[32m')"
color_yellow="$(printf '\033[33m')"
color_blue="$(printf '\033[34m')"
color_cyan="$(printf '\033[36m')"

json_get() {
    local filter="$1"
    jq -r "$filter // empty" <<<"$input"
}

safe_session_id() {
    local raw="$1"
    if [ -z "$raw" ]; then
        raw="no-session"
    fi
    printf "%s" "$raw" | tr -c 'A-Za-z0-9._-' '_'
}

colorize() {
    local color="$1"
    local text="$2"
    printf "%b%s%b" "$color" "$text" "$color_reset"
}

state_indicator() {
    local label="$1"
    local state="$2"

    case "$state" in
        ok)
            colorize "$color_green" "$label"
            ;;
        warn)
            colorize "$color_yellow" "$label"
            ;;
        bad)
            colorize "$color_red" "$label"
            ;;
        info)
            colorize "$color_blue" "$label"
            ;;
        *)
            colorize "$color_dim" "$label"
            ;;
    esac
}

branch_name() {
    local dir="$1"

    if [ -z "$dir" ] || ! command -v git >/dev/null 2>&1; then
        return 0
    fi

    git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null || true
}

dirty_marker() {
    local dir="$1"

    if [ -z "$dir" ] || ! command -v git >/dev/null 2>&1; then
        return 0
    fi

    if [ -n "$(git -C "$dir" status --porcelain 2>/dev/null | head -n 1)" ]; then
        printf "*"
    fi
}

session_id="$(json_get '.session_id')"
cwd="$(json_get '.workspace.current_dir')"
if [ -z "$cwd" ]; then
    cwd="$(json_get '.cwd')"
fi
model="$(json_get '.model.display_name')"
if [ -z "$model" ]; then
    model="unknown-model"
fi

repo_name="${cwd##*/}"
branch="$(branch_name "$cwd")"
dirty="$(dirty_marker "$cwd")"

state_file="${HOME}/.claude/state/$(safe_session_id "$session_id").json"
task_type="other"
tests_ok="false"
tests_failed="false"
lint_ok="false"
lint_failed="false"
build_ok="false"
build_failed="false"
stop_block_reason=""
docs_changed="false"
started_json='[]'

if [ -f "$state_file" ]; then
    task_type="$(jq -r '.task_type // "other"' "$state_file")"
    tests_ok="$(jq -r '.tests_ok // false' "$state_file")"
    tests_failed="$(jq -r '.tests_failed // false' "$state_file")"
    lint_ok="$(jq -r '.lint_ok // false' "$state_file")"
    lint_failed="$(jq -r '.lint_failed // false' "$state_file")"
    build_ok="$(jq -r '.build_ok // false' "$state_file")"
    build_failed="$(jq -r '.build_failed // false' "$state_file")"
    stop_block_reason="$(jq -r '.stop_block_reason // empty' "$state_file")"
    docs_changed="$(jq -r '.docs_changed // false' "$state_file")"
    started_json="$(jq -c '.subagents_started // []' "$state_file")"
fi

has_started() {
    local alias="$1"
    jq -e --arg alias "$alias" 'index($alias) != null' <<<"$started_json" >/dev/null 2>&1
}

verification_state="warn"
if [ "$tests_failed" = "true" ] || [ "$lint_failed" = "true" ] || [ "$build_failed" = "true" ]; then
    verification_state="bad"
elif [ "$tests_ok" = "true" ] || [ "$lint_ok" = "true" ] || [ "$build_ok" = "true" ]; then
    verification_state="ok"
fi

review_state="warn"
if has_started "cr"; then
    review_state="ok"
fi

workflow_tokens=()
workflow_ok="false"

case "$task_type" in
    bugfix)
        if has_started "bug"; then
            bug_state="ok"
            exp_state="dim"
            dbg_state="dim"
            workflow_ok="true"
        elif has_started "e"; then
            bug_state="dim"
            exp_state="ok"
            dbg_state="dim"
            workflow_ok="true"
        elif has_started "dbg"; then
            bug_state="dim"
            exp_state="dim"
            dbg_state="ok"
            workflow_ok="true"
        else
            bug_state="warn"
            exp_state="warn"
            dbg_state="warn"
        fi
        workflow_tokens+=("$(state_indicator "BUG" "$bug_state")")
        workflow_tokens+=("$(state_indicator "EXP" "$exp_state")")
        workflow_tokens+=("$(state_indicator "DBG" "$dbg_state")")
        ;;
    feature)
        if has_started "e"; then
            exp_state="ok"
            arc_state="dim"
            workflow_ok="true"
        elif has_started "a"; then
            exp_state="dim"
            arc_state="ok"
            workflow_ok="true"
        else
            exp_state="warn"
            arc_state="warn"
        fi
        workflow_tokens+=("$(state_indicator "EXP" "$exp_state")")
        workflow_tokens+=("$(state_indicator "ARC" "$arc_state")")
        ;;
    refactor)
        if has_started "hk"; then
            hk_state="ok"
            exp_state="dim"
            arc_state="dim"
            workflow_ok="true"
        elif has_started "e"; then
            hk_state="dim"
            exp_state="ok"
            arc_state="dim"
            workflow_ok="true"
        elif has_started "a"; then
            hk_state="dim"
            exp_state="dim"
            arc_state="ok"
            workflow_ok="true"
        else
            hk_state="warn"
            exp_state="warn"
            arc_state="warn"
        fi
        workflow_tokens+=("$(state_indicator "HK" "$hk_state")")
        workflow_tokens+=("$(state_indicator "EXP" "$exp_state")")
        workflow_tokens+=("$(state_indicator "ARC" "$arc_state")")
        ;;
    review)
        workflow_ok="$([ "$review_state" = "ok" ] && printf "true" || printf "false")"
        ;;
    docs)
        if has_started "doc"; then
            doc_state="ok"
            workflow_ok="true"
        else
            doc_state="warn"
        fi
        workflow_tokens+=("$(state_indicator "DOC" "$doc_state")")
        ;;
    *)
        ;;
esac

if [ "$docs_changed" = "true" ] && [ "$task_type" != "docs" ]; then
    workflow_tokens+=("$(state_indicator "DOC" "info")")
fi

overall="WAIT"
overall_state="warn"

if [ -n "$stop_block_reason" ]; then
    overall="BLOCK"
    overall_state="bad"
elif [ "$verification_state" = "ok" ] && [ "$review_state" = "ok" ] && [ "$workflow_ok" = "true" ]; then
    overall="OK"
    overall_state="ok"
fi

first_line_parts=()
first_line_parts+=("$(colorize "$color_cyan" "${repo_name:-repo}")")
if [ -n "$branch" ]; then
    first_line_parts+=("$(colorize "$color_blue" "${branch}${dirty}")")
fi
first_line_parts+=("$(colorize "$color_green" "$model")")
if [ -n "$task_type" ] && [ "$task_type" != "other" ]; then
    first_line_parts+=("$(colorize "$color_yellow" "$task_type")")
fi

second_line_parts=()
second_line_parts+=("$(state_indicator "VER" "$verification_state")")
second_line_parts+=("$(state_indicator "CR" "$review_state")")
second_line_parts+=("${workflow_tokens[@]}")
second_line_parts+=("$(state_indicator "$overall" "$overall_state")")

printf "%s\n" "$(IFS=' | '; printf "%s" "${first_line_parts[*]}")"
printf "%s" "$(IFS=' '; printf "%s" "${second_line_parts[*]}")"

if [ -n "$stop_block_reason" ]; then
    short_reason="$(printf "%s" "$stop_block_reason" | cut -c1-80)"
    printf "  %s" "$(colorize "$color_red" "$short_reason")"
fi
printf "\n"
