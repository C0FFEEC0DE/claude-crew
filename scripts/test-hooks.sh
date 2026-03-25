#!/bin/bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASES_FILE="${1:-$REPO_ROOT/tests/hooks/cases.json}"
TMP_ROOT="$(mktemp -d)"
FAILURES=0
TOTAL=0

cleanup() {
    rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

safe_session_id() {
    printf "%s" "$1" | tr -c 'A-Za-z0-9._-' '_'
}

resolve_placeholders() {
    local value="$1"
    local case_tmp="$2"
    local case_home="$3"

    value="${value//__CASE_TMP__/$case_tmp}"
    value="${value//__CASE_HOME__/$case_home}"
    value="${value//__REPO_ROOT__/$REPO_ROOT}"
    printf "%s" "$value"
}

print_failure() {
    local name="$1"
    local message="$2"
    echo "FAIL: $name - $message"
    FAILURES=$((FAILURES + 1))
}

run_case() {
    local case_json="$1"
    local name script_path stdin_path cwd expected_exit stdout_regex stderr_regex stdout_jq state_jq
    local case_tmp case_home stdout_file stderr_file workdir session_id state_seed state_file
    local exit_code

    name="$(jq -r '.name' <<<"$case_json")"
    script_path="$(jq -r '.script' <<<"$case_json")"
    stdin_path="$(jq -r '.stdin' <<<"$case_json")"
    cwd="$(jq -r '.cwd // "."' <<<"$case_json")"
    expected_exit="$(jq -r '.expect_exit // 0' <<<"$case_json")"
    stdout_regex="$(jq -r '.stdout_regex // empty' <<<"$case_json")"
    stderr_regex="$(jq -r '.stderr_regex // empty' <<<"$case_json")"
    stdout_jq="$(jq -r '.stdout_jq // empty' <<<"$case_json")"
    state_jq="$(jq -r '.state_jq // empty' <<<"$case_json")"
    state_seed="$(jq -r '.seed_state // empty' <<<"$case_json")"

    TOTAL=$((TOTAL + 1))
    case_tmp="$TMP_ROOT/$name"
    case_home="$case_tmp/home"
    stdout_file="$case_tmp/stdout"
    stderr_file="$case_tmp/stderr"
    workdir="$REPO_ROOT/$cwd"

    mkdir -p "$case_home/.claude/state" "$case_tmp"

    session_id="$(jq -r '.session_id // empty' "$REPO_ROOT/$stdin_path")"
    if [ -n "$state_seed" ]; then
        if [ -z "$session_id" ]; then
            print_failure "$name" "seed_state requires session_id in fixture"
            return
        fi
        state_file="$case_home/.claude/state/$(safe_session_id "$session_id").json"
        cp "$REPO_ROOT/$state_seed" "$state_file"
    fi

    mapfile -t env_pairs < <(jq -r '.env // {} | to_entries[] | "\(.key)=\(.value)"' <<<"$case_json")
    resolved_env=()
    for pair in "${env_pairs[@]}"; do
        key="${pair%%=*}"
        value="${pair#*=}"
        value="$(resolve_placeholders "$value" "$case_tmp" "$case_home")"
        resolved_env+=("$key=$value")
    done

    set +e
    (
        cd "$workdir"
        env HOME="$case_home" "${resolved_env[@]}" "$REPO_ROOT/$script_path" \
            < "$REPO_ROOT/$stdin_path" \
            > "$stdout_file" \
            2> "$stderr_file"
    )
    exit_code=$?
    set -e

    if [ "$exit_code" -ne "$expected_exit" ]; then
        print_failure "$name" "expected exit $expected_exit, got $exit_code"
        return
    fi

    if [ -n "$stdout_regex" ] && ! grep -Eq "$stdout_regex" "$stdout_file"; then
        print_failure "$name" "stdout did not match regex: $stdout_regex"
        return
    fi

    if [ -n "$stderr_regex" ] && ! grep -Eq "$stderr_regex" "$stderr_file"; then
        print_failure "$name" "stderr did not match regex: $stderr_regex"
        return
    fi

    if [ -n "$stdout_jq" ] && ! jq -e "$stdout_jq" "$stdout_file" >/dev/null 2>&1; then
        print_failure "$name" "stdout JSON assertion failed: $stdout_jq"
        return
    fi

    if [ -n "$state_jq" ]; then
        if [ -z "$session_id" ]; then
            print_failure "$name" "state assertion requires session_id in fixture"
            return
        fi
        state_file="$case_home/.claude/state/$(safe_session_id "$session_id").json"
        if [ ! -f "$state_file" ]; then
            print_failure "$name" "expected state file not found: $state_file"
            return
        fi
        if ! jq -e "$state_jq" "$state_file" >/dev/null 2>&1; then
            print_failure "$name" "state assertion failed: $state_jq"
            return
        fi
    fi

    while IFS= read -r file_assertion; do
        [ -z "$file_assertion" ] && continue
        file_path="$(jq -r '.path' <<<"$file_assertion")"
        file_regex="$(jq -r '.regex' <<<"$file_assertion")"
        resolved_path="$(resolve_placeholders "$file_path" "$case_tmp" "$case_home")"
        if [ ! -f "$resolved_path" ]; then
            print_failure "$name" "expected file not found: $resolved_path"
            return
        fi
        if ! grep -Eq "$file_regex" "$resolved_path"; then
            print_failure "$name" "file assertion failed for $resolved_path: $file_regex"
            return
        fi
    done < <(jq -c '.file_assertions[]?' <<<"$case_json")

    echo "PASS: $name"
}

echo "=== Hook Behavior Tests ==="
echo "Manifest: $CASES_FILE"
echo ""

while IFS= read -r case_json; do
    run_case "$case_json"
done < <(jq -c '.[]' "$CASES_FILE")

echo ""
echo "=== Summary ==="
echo "Cases: $TOTAL"
if [ "$FAILURES" -eq 0 ]; then
    echo "All hook behavior tests passed!"
    exit 0
fi

echo "Failures: $FAILURES"
exit 1
