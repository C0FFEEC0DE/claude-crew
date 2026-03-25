#!/bin/bash

set -euo pipefail

HOOK_INPUT="$(cat)"
STATE_ROOT="${HOME}/.claude/state"
LOG_ROOT="${HOME}/.claude/logs"

json_get() {
    local filter="$1"
    jq -r "$filter // empty" <<<"$HOOK_INPUT"
}

json_get_bool() {
    local filter="$1"
    jq -r "if ($filter) == true then \"true\" else \"false\" end" <<<"$HOOK_INPUT"
}

timestamp_utc() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

safe_session_id() {
    local raw
    raw="$(json_get '.session_id')"
    if [ -z "$raw" ]; then
        raw="no-session"
    fi
    printf "%s" "$raw" | tr -c 'A-Za-z0-9._-' '_'
}

state_file() {
    printf "%s/%s.json" "$STATE_ROOT" "$(safe_session_id)"
}

ensure_dirs() {
    mkdir -p "$STATE_ROOT" "$LOG_ROOT"
}

ensure_state() {
    local file
    file="$(state_file)"
    ensure_dirs
    if [ -f "$file" ]; then
        return
    fi

    jq -n \
        --arg session_id "$(json_get '.session_id')" \
        --arg cwd "$(json_get '.cwd')" \
        --arg transcript_path "$(json_get '.transcript_path')" \
        --arg created_at "$(timestamp_utc)" \
        '{
            session_id: $session_id,
            cwd: $cwd,
            transcript_path: $transcript_path,
            created_at: $created_at,
            task_type: "other",
            edited: false,
            code_changed: false,
            docs_changed: false,
            tests_ok: false,
            tests_failed: false,
            lint_ok: false,
            lint_failed: false,
            build_ok: false,
            build_failed: false,
            last_test_command: "",
            last_lint_command: "",
            last_build_command: "",
            files: []
        }' > "$file"
}

update_state() {
    local jq_program="$1"
    local file
    local tmp

    file="$(state_file)"
    tmp="$(mktemp)"
    jq "$jq_program" "$file" > "$tmp"
    mv "$tmp" "$file"
}

append_jsonl() {
    local name="$1"
    local payload="$2"
    ensure_dirs
    printf "%s\n" "$payload" >> "${LOG_ROOT}/${name}"
}

emit_context() {
    local event_name="$1"
    local message="$2"
    jq -n \
        --arg event_name "$event_name" \
        --arg message "$message" \
        '{
            hookSpecificOutput: {
                hookEventName: $event_name,
                additionalContext: $message
            }
        }'
}

emit_pretool_decision() {
    local decision="$1"
    local reason="$2"
    jq -n \
        --arg decision "$decision" \
        --arg reason "$reason" \
        '{
            hookSpecificOutput: {
                hookEventName: "PreToolUse",
                permissionDecision: $decision,
                permissionDecisionReason: $reason
            }
        }'
}

detect_node_script() {
    local script_name="$1"
    if [ -f package.json ] && jq -e --arg name "$script_name" '.scripts[$name] != null' package.json >/dev/null 2>&1; then
        printf "npm run %s" "$script_name"
        return 0
    fi
    return 1
}

detect_test_cmd() {
    local cmd=""

    if cmd="$(detect_node_script test)"; then
        printf "%s" "$cmd"
        return 0
    fi
    if [ -f Cargo.toml ]; then
        printf "cargo test"
        return 0
    fi
    if [ -f go.mod ]; then
        printf "go test ./..."
        return 0
    fi
    if [ -f pytest.ini ] || [ -f pyproject.toml ] || [ -d tests ]; then
        printf "pytest"
        return 0
    fi

    return 1
}

detect_lint_cmd() {
    local cmd=""

    if cmd="$(detect_node_script lint)"; then
        printf "%s" "$cmd"
        return 0
    fi
    if [ -f Cargo.toml ]; then
        printf "cargo clippy --all-targets --all-features -- -D warnings"
        return 0
    fi
    if [ -f pyproject.toml ] || [ -d tests ]; then
        printf "python -m compileall ."
        return 0
    fi

    return 1
}

detect_build_cmd() {
    local cmd=""

    if cmd="$(detect_node_script build)"; then
        printf "%s" "$cmd"
        return 0
    fi
    if [ -f Cargo.toml ]; then
        printf "cargo build"
        return 0
    fi
    if [ -f go.mod ]; then
        printf "go build ./..."
        return 0
    fi
    if [ -f Makefile ] || [ -f makefile ]; then
        printf "make"
        return 0
    fi

    return 1
}

command_class() {
    local command="$1"

    case "$command" in
        *"pytest"*|*"npm test"*|*"npm run test"*|*"pnpm test"*|*"yarn test"*|*"cargo test"*|*"go test"*|*"ctest"*|*"make test"*)
            printf "test"
            ;;
        *"npm run lint"*|*"pnpm lint"*|*"yarn lint"*|*"ruff"*|*"flake8"*|*"cargo clippy"*|*"golangci-lint"*|*"eslint"*|*"shellcheck"*|*"python -m compileall "*)
            printf "lint"
            ;;
        *"npm run build"*|*"pnpm build"*|*"yarn build"*|*"cargo build"*|*"go build"*|*"cmake --build"*|*"make"*)
            printf "build"
            ;;
        *)
            printf "other"
            ;;
    esac
}

is_docs_path() {
    local file_path="$1"

    case "$file_path" in
        *.md|*.mdx|*.txt|*.rst|*.adoc|*.markdown|*/docs/*|README*|CHANGELOG*|CLAUDE.md)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}
