#!/usr/bin/env python3

import difflib
import json
import os
import pathlib
import re
import subprocess
import sys
import time


REPO_ROOT = pathlib.Path(os.environ["BENCH_REPO_ROOT"]).resolve()
TASK_FILE = pathlib.Path(os.environ["BENCH_TASK_FILE"]).resolve()
WORKDIR = pathlib.Path(os.environ["BENCH_WORKDIR"]).resolve()
OUTPUT_DIR = pathlib.Path(os.environ["BENCH_OUTPUT_DIR"]).resolve()


def env_or_default(name: str, default: str) -> str:
    value = os.environ.get(name, "")
    value = value.strip()
    return value or default


CLAUDE_BIN = env_or_default("CLAUDE_BIN", "claude")
CLAUDE_MODEL = env_or_default(
    "CLAUDE_MODEL", env_or_default("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
)
MAX_TURNS = env_or_default("MAX_TURNS", "8")


def is_docs_path(path_str: str) -> bool:
    path_lower = path_str.lower()
    name = pathlib.Path(path_lower).name
    return (
        path_lower.endswith((".md", ".mdx", ".txt", ".rst", ".adoc", ".markdown"))
        or "/docs/" in path_lower
        or name.startswith("readme")
        or name.startswith("changelog")
        or name == "claude.md"
    )


def is_ignored_runtime_path(path: pathlib.Path) -> bool:
    ignored_parts = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    return any(part in ignored_parts for part in path.parts) or path.name == ".coverage"


def snapshot_files(root: pathlib.Path) -> dict[str, str]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or is_ignored_runtime_path(path.relative_to(root)):
            continue
        snapshot[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return snapshot


def build_patch(before: dict[str, str], after: dict[str, str]) -> str:
    chunks: list[str] = []
    for rel_path in sorted(set(before) | set(after)):
        old = before.get(rel_path)
        new = after.get(rel_path)
        if old == new:
            continue
        old_lines = [] if old is None else old.splitlines(keepends=True)
        new_lines = [] if new is None else new.splitlines(keepends=True)
        chunks.extend(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            )
        )
    return "".join(chunks)


def build_prompt(task: dict) -> str:
    success_criteria = "\n".join(f"- {item}" for item in task.get("success_criteria", []))
    must_not = "\n".join(f"- {item}" for item in task.get("must_not", []))
    return f"""You are running in a tiny benchmark repository fixture.

Complete the task in the current working directory using the installed Claude Code profile from ~/.claude.
Use tools normally. Make only the changes needed for this task. Do not do release or deploy work.
If behavior changes, update docs. If verification is required, run the relevant tests locally.
Leave the workspace changes in place for artifact collection.

Task metadata:
- id: {task["id"]}
- category: {task["category"]}
- review_required: {json.dumps(bool(task["review_required"]))}
- docs_required: {json.dumps(bool(task["docs_required"]))}
- verification_required: {json.dumps(bool(task["verification_required"]))}

Task:
{task["prompt"]}

Success criteria:
{success_criteria or "- none provided"}

Must not:
{must_not or "- none provided"}

Final response requirements:
- Keep it concise.
- Include a line starting with "Verification status:"
- Include a line starting with "Review outcome:"
- Include a line starting with "Remaining risks:"
"""


def run_claude(prompt: str, debug_log_path: pathlib.Path) -> tuple[int, str, str]:
    command = [
        CLAUDE_BIN,
        "-p",
        prompt,
        "--model",
        CLAUDE_MODEL,
        "--max-turns",
        MAX_TURNS,
        "--permission-mode",
        "acceptEdits",
        "--debug-file",
        str(debug_log_path),
        "--output-format",
        "json",
    ]
    completed = subprocess.run(
        command,
        cwd=WORKDIR,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout, completed.stderr


def extract_result_text(raw_json: str) -> tuple[dict | None, str]:
    if not raw_json.strip():
        return None, ""
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return None, ""
    return payload, str(payload.get("result", "") or "")


def run_verification() -> tuple[bool, bool, str]:
    tests_exist = any(WORKDIR.glob("test_*.py")) or any(WORKDIR.glob("tests/*.py"))
    if not tests_exist:
        return False, False, "No Python test files were found in the fixture."

    command = [sys.executable, "-m", "pytest", "-q"]
    completed = subprocess.run(
        command,
        cwd=WORKDIR,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return True, completed.returncode == 0, output


def has_line_prefix(text: str, prefix: str) -> bool:
    pattern = r"(?im)^\s*" + re.escape(prefix)
    return re.search(pattern, text) is not None


def truncate(text: str, limit: int = 1200) -> str:
    clean = text.strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def write_text(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def payload_keys(payload: dict | None) -> str:
    if not isinstance(payload, dict):
        return "<invalid-or-missing>"
    return ", ".join(sorted(payload.keys())) or "<empty-object>"


def payload_string(payload: dict | None, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get(key, "")
    return value if isinstance(value, str) else str(value or "")


def payload_permission_denials(payload: dict | None) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    value = payload.get("permission_denials", [])
    return value if isinstance(value, list) else []


def first_permission_denial_summary(denials: list[dict]) -> str:
    if not denials:
        return "none"
    first = denials[0]
    tool_name = first.get("tool_name", "unknown")
    tool_input = first.get("tool_input", {})
    file_path = ""
    if isinstance(tool_input, dict):
        file_path = str(tool_input.get("file_path", "") or "")
    if file_path:
        return f"{tool_name} -> {file_path}"
    return str(tool_name)


def build_task_summary(
    task: dict,
    prompt: str,
    status: str,
    exit_code: int,
    changed_files: list[str],
    failures: list[str],
    raw_json: str,
    payload: dict | None,
    payload_subtype: str,
    payload_stop_reason: str,
    permission_denials: list[dict],
    result_text: str,
    verification_output: str,
    stderr_text: str,
    debug_log_text: str,
    patch_text: str,
) -> str:
    lines = [
        f"Task: {task['id']}",
        f"Category: {task['category']}",
        f"Status: {status}",
        f"Claude exit code: {exit_code}",
        f"Review required: {bool(task['review_required'])}",
        f"Docs required: {bool(task['docs_required'])}",
        f"Verification required: {bool(task['verification_required'])}",
        f"Changed files: {', '.join(changed_files) if changed_files else 'none'}",
        f"Failures: {', '.join(failures) if failures else 'none'}",
        f"Claude payload keys: {payload_keys(payload)}",
        f"Claude subtype: {payload_subtype or '<missing>'}",
        f"Claude stop reason: {payload_stop_reason or '<missing>'}",
        f"Permission denials: {len(permission_denials)}",
        f"First permission denial: {first_permission_denial_summary(permission_denials)}",
        f"stdout bytes: {len(raw_json.encode('utf-8'))}",
        f"stderr bytes: {len(stderr_text.encode('utf-8'))}",
        "",
        "Prompt excerpt:",
        truncate(prompt, 1200) or "<missing>",
        "",
        "Raw Claude JSON excerpt:",
        truncate(raw_json, 1200) or "<missing>",
        "",
        "Result excerpt:",
        truncate(result_text, 1200) or "<missing>",
        "",
        "Verification excerpt:",
        truncate(verification_output, 1200) or "<not run>",
        "",
        "stderr excerpt:",
        truncate(stderr_text, 1200) or "<empty>",
        "",
        "debug log excerpt:",
        truncate(debug_log_text, 1600) or "<empty>",
        "",
        "Patch excerpt:",
        truncate(patch_text, 1200) or "<empty>",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = time.monotonic()
    task = json.loads(TASK_FILE.read_text(encoding="utf-8"))
    before = snapshot_files(WORKDIR)

    prompt = build_prompt(task)
    exit_code = 0
    raw_stdout = ""
    raw_stderr = ""
    payload = None
    result_text = ""
    fatal_error = ""
    debug_log_path = OUTPUT_DIR / "claude-debug.log"

    try:
        exit_code, raw_stdout, raw_stderr = run_claude(prompt, debug_log_path)
        payload, result_text = extract_result_text(raw_stdout)
        if not raw_stdout.strip():
            fatal_error = "Claude output JSON is missing or empty."
        elif payload is None:
            fatal_error = "Claude output JSON is invalid."
        elif not result_text.strip():
            fatal_error = "Claude result text is missing or empty."
    except Exception as exc:
        fatal_error = f"Claude runner exception: {exc}"

    write_text(OUTPUT_DIR / "claude-result.json", raw_stdout)
    write_text(OUTPUT_DIR / "claude-result.txt", result_text)
    write_text(OUTPUT_DIR / "claude-stderr.log", raw_stderr)
    debug_log_text = debug_log_path.read_text(encoding="utf-8") if debug_log_path.exists() else ""
    payload_subtype = payload_string(payload, "subtype")
    payload_stop_reason = payload_string(payload, "stop_reason")
    permission_denials = payload_permission_denials(payload)
    if raw_stderr.strip():
        write_text(OUTPUT_DIR / "claude-stderr-tail.txt", "\n".join(raw_stderr.splitlines()[-200:]) + "\n")

    after = snapshot_files(WORKDIR)
    changed_files = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    docs_updated = any(is_docs_path(path) for path in changed_files)
    non_doc_changed_files = [path for path in changed_files if not is_docs_path(path)]
    completed = len(changed_files) > 0

    patch_text = build_patch(before, after)
    write_text(OUTPUT_DIR / "workspace.patch", patch_text)
    write_text(OUTPUT_DIR / "changed-files.json", json.dumps(changed_files, ensure_ascii=False, indent=2) + "\n")
    write_text(OUTPUT_DIR / "task-prompt.txt", prompt + "\n")

    verification_required = bool(task["verification_required"])
    tests_run = False
    tests_passed = False
    verification_output = ""
    if verification_required:
        tests_run, tests_passed, verification_output = run_verification()

    review_required = bool(task["review_required"])
    docs_required = bool(task["docs_required"])
    verification_summary_present = has_line_prefix(result_text, "Verification status:")
    review_present = has_line_prefix(result_text, "Review outcome:")
    risks_present = has_line_prefix(result_text, "Remaining risks:")

    status = "passed"
    failures: list[str] = []

    if exit_code != 0:
        failures.append(f"claude_exit_code={exit_code}")
    if fatal_error:
        failures.append(fatal_error)
    if not completed:
        failures.append("workspace_changed=false")
    if verification_required and not tests_run:
        failures.append("verification_not_run")
    if verification_required and not tests_passed:
        failures.append("verification_failed")
    if verification_required and not verification_summary_present:
        failures.append("verification_summary_missing")
    if review_required and not review_present:
        failures.append("review_summary_missing")
    if not risks_present:
        failures.append("risk_summary_missing")
    if docs_required and not docs_updated:
        failures.append("docs_not_updated")
    if task["category"] == "docs" and non_doc_changed_files:
        failures.append("docs_task_changed_non_docs")

    if failures:
        status = "failed"

    runtime_seconds = round(time.monotonic() - started_at, 3)
    notes = (
        f"Claude model={CLAUDE_MODEL}. "
        f"Exit code: {exit_code}. "
        f"Changed files: {', '.join(changed_files) if changed_files else 'none'}. "
        f"Failures: {', '.join(failures) if failures else 'none'}. "
        f"Result: {truncate(result_text, 700) or 'missing'}. "
        f"Verification: {truncate(verification_output, 700) or 'not required'}"
    )

    result = {
        "task_id": task["id"],
        "status": status,
        "completed": completed,
        "verification_required": verification_required,
        "tests_run": tests_run,
        "tests_passed": tests_passed,
        "review_required": review_required,
        "review_present": review_present,
        "docs_required": docs_required,
        "docs_updated": docs_updated,
        "policy_violations": 0,
        "tool_failures": 0 if status == "passed" else 1,
        "runtime_seconds": runtime_seconds,
        "notes": notes,
        "category": task["category"],
        "changed_files": changed_files,
        "non_doc_changed_files": non_doc_changed_files,
        "verification_summary_present": verification_summary_present,
        "risk_summary_present": risks_present,
        "claude_exit_code": exit_code,
        "claude_subtype": payload_subtype,
        "claude_stop_reason": payload_stop_reason,
        "permission_denials_count": len(permission_denials),
        "first_permission_denial": first_permission_denial_summary(permission_denials),
        "fatal_error": fatal_error,
        "failures": failures,
    }

    write_text(OUTPUT_DIR / "result.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    write_text(
        OUTPUT_DIR / "task-summary.txt",
        build_task_summary(
            task=task,
            prompt=prompt,
            status=status,
            exit_code=exit_code,
            changed_files=changed_files,
            failures=failures,
            raw_json=raw_stdout,
            payload=payload,
            payload_subtype=payload_subtype,
            payload_stop_reason=payload_stop_reason,
            permission_denials=permission_denials,
            result_text=result_text,
            verification_output=verification_output,
            stderr_text=raw_stderr,
            debug_log_text=debug_log_text,
            patch_text=patch_text,
        ),
    )
    if fatal_error:
        write_text(OUTPUT_DIR / "runner-error.txt", fatal_error + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
