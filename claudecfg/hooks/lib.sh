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
            detected_test_command: "",
            detected_lint_command: "",
            detected_build_command: "",
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

emit_permission_request_deny() {
    local message="$1"
    jq -n \
        --arg message "$message" \
        '{
            hookSpecificOutput: {
                hookEventName: "PermissionRequest",
                decision: {
                    behavior: "deny",
                    message: $message
                }
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
        *"npm run lint"*|*"pnpm lint"*|*"yarn lint"*|*"ruff"*|*"flake8"*|*"cargo clippy"*|*"golangci-lint"*|*"eslint"*|*"shellcheck"*|*"python -m compileall "*|*"make lint"*)
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

is_release_or_deploy_command() {
    local command="$1"

    [[ "$command" == *"npm publish"* \
        || "$command" == *"cargo publish"* \
        || "$command" == *"docker push"* \
        || "$command" == *"gh release"* \
        || "$command" == *"kubectl apply"* \
        || "$command" == *"helm upgrade"* ]]
}

is_remote_shell_bootstrap_command() {
    local command="$1"

    if { [[ "$command" =~ (^|[[:space:]])curl($|[[:space:]]) ]] || [[ "$command" =~ (^|[[:space:]])wget($|[[:space:]]) ]]; } \
        && [[ "$command" =~ [|][[:space:]]*[[:alnum:]_./-]*(sh|bash|zsh|dash|ksh)($|[[:space:]]) ]]; then
        return 0
    fi

    return 1
}

message_mentions_verification_status() {
    local message="$1"

    grep -Eiq '(verification|verified|validate|validated|test|tests|pytest|coverage|lint|build|compiled|compile|pass(ed)?|fail(ed)?|проверк|вериф|тест|линт|сборк)' <<<"$message"
}

message_mentions_review_outcome() {
    local message="$1"

    grep -Eiq '(review (pending|complete|completed|done|not run)|reviewed|code review|self-review|ревью (в ожидании|готово|сделано|не проводилось)|самопровер)' <<<"$message"
}

message_mentions_changed_files() {
    local message="$1"

    grep -Eiq '(files changed|changed files|updated files|modified files|key changed files|no files changed|измененн(ые|ых) файл|файлы изменены|файлы:|changed:)' <<<"$message"
}

message_mentions_remaining_risks() {
    local message="$1"

    grep -Eiq '(remaining risks|risks:|risk: none|risks: none|no known risks|residual risk|остаточн(ые|ых) риски|риски: нет|риски отсутствуют|remaining risk: none)' <<<"$message"
}

message_mentions_next_step() {
    local message="$1"

    grep -Eiq '(next step|next steps|next:|follow-up|follow up|pending next|следующ(ий|ие) шаг|дальше:|следующее:)' <<<"$message"
}

message_mentions_concrete_outcome() {
    local message="$1"

    grep -Eiq '(outcome|result|implemented|updated|fixed|investigated|reviewed|documented|added|removed|refactored|changed|created|no changes|completed|done|исправил|обновил|добавил|удалил|проверил|нашел|сделал|без изменений)' <<<"$message"
}

session_block_reason() {
    local state code_changed tests_ok tests_failed lint_ok lint_failed build_ok build_failed
    local detected_test_command detected_lint_command detected_build_command
    local last_test_command last_lint_command last_build_command
    local has_detected_verification="false"
    local has_successful_verification="false"

    state="$(state_file)"
    code_changed="$(jq -r '.code_changed // false' "$state")"
    tests_ok="$(jq -r '.tests_ok // false' "$state")"
    tests_failed="$(jq -r '.tests_failed // false' "$state")"
    lint_ok="$(jq -r '.lint_ok // false' "$state")"
    lint_failed="$(jq -r '.lint_failed // false' "$state")"
    build_ok="$(jq -r '.build_ok // false' "$state")"
    build_failed="$(jq -r '.build_failed // false' "$state")"
    detected_test_command="$(jq -r '.detected_test_command // empty' "$state")"
    detected_lint_command="$(jq -r '.detected_lint_command // empty' "$state")"
    detected_build_command="$(jq -r '.detected_build_command // empty' "$state")"
    last_test_command="$(jq -r '.last_test_command // empty' "$state")"
    last_lint_command="$(jq -r '.last_lint_command // empty' "$state")"
    last_build_command="$(jq -r '.last_build_command // empty' "$state")"

    if [ -n "$detected_test_command" ] || [ -n "$detected_lint_command" ] || [ -n "$detected_build_command" ]; then
        has_detected_verification="true"
    fi

    if [ "$tests_ok" = "true" ] || [ "$lint_ok" = "true" ] || [ "$build_ok" = "true" ]; then
        has_successful_verification="true"
    fi

    if [ "$code_changed" = "true" ] && [ "$tests_failed" = "true" ]; then
        printf "Code or config changed, but the latest test command failed in this session (%s). Fix the failure and rerun verification before stopping." "${last_test_command:-test command}"
        return 0
    fi

    if [ "$code_changed" = "true" ] && [ "$lint_failed" = "true" ]; then
        printf "Code or config changed, but the latest lint/static-check command failed in this session (%s). Fix the failure and rerun it successfully before stopping." "${last_lint_command:-lint command}"
        return 0
    fi

    if [ "$code_changed" = "true" ] && [ "$build_failed" = "true" ]; then
        printf "Code or config changed, but the latest build command failed in this session (%s). Fix the failure and rerun it successfully before stopping." "${last_build_command:-build command}"
        return 0
    fi

    if [ "$code_changed" = "true" ] && [ "$has_detected_verification" = "true" ] && [ "$has_successful_verification" != "true" ]; then
        printf "Code or config changed, but no successful verification command was recorded in this session. Run a detected test, lint, or build command before stopping."
        return 0
    fi

    return 1
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
