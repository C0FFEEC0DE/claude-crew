#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import re
from typing import Iterable


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TASKS_ROOT = REPO_ROOT / "bench" / "tasks"

SUITE_DEFAULTS = {
    "smoke": "bench/tasks/smoke/*.json",
    "full": "bench/tasks/full/*.json",
    "subagents_smoke": "bench/tasks/subagents/smoke/*.json",
    "subagents_golden": "bench/tasks/subagents/golden/*.json",
}

GLOBAL_BEHAVIOR_PREFIXES = (
    "claudecfg/hooks/",
    "claudecfg/settings.json",
    "scripts/assert-benchmark-summary.sh",
    "scripts/bench_runner_claude_code.py",
    "scripts/collect-benchmark-changes.sh",
    "scripts/run-benchmark.sh",
    "scripts/select-benchmark-tasks.py",
)

GLOBAL_BEHAVIOR_FILES = {
    "CLAUDE.md",
    "install.sh",
    "claudecfg/install.sh",
    ".github/workflows/behavior-benchmark.yml",
    ".github/workflows/behavior-benchmark-full.yml",
    ".github/workflows/behavior-benchmark-subagents-smoke.yml",
    ".github/workflows/benchmark-nightly.yml",
}


def frontmatter_field(path: pathlib.Path, field: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    match = re.search(rf"(?m)^{re.escape(field)}:\s*(.+)$", text)
    if not match:
        return None
    return match.group(1).strip()


def build_agent_file_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted((REPO_ROOT / "claudecfg" / "agents").glob("*.md")):
        alias = frontmatter_field(path, "alias")
        if alias:
            mapping[path.name] = alias
    return mapping


def build_agent_name_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted((REPO_ROOT / "claudecfg" / "agents").glob("*.md")):
        alias = frontmatter_field(path, "alias")
        name = frontmatter_field(path, "name")
        if alias:
            mapping[alias.casefold()] = alias
        if alias and name:
            mapping[name.casefold()] = alias
    return mapping


def build_skill_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted((REPO_ROOT / "claudecfg" / "skills").glob("*.md")):
        agent = frontmatter_field(path, "agent")
        alias = AGENT_NAME_TO_ALIAS.get(agent.casefold()) if agent else None
        if alias:
            mapping[path.name] = alias
    return mapping


AGENT_FILE_TO_ALIAS = build_agent_file_map()
AGENT_NAME_TO_ALIAS = build_agent_name_map()
SKILL_TO_ALIAS = build_skill_map()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True, choices=sorted(SUITE_DEFAULTS))
    parser.add_argument("--changed-files-file")
    parser.add_argument("--selection-mode", choices=("all", "changed"), default="changed")
    parser.add_argument("--exclude-overlap-with-suite", choices=sorted(SUITE_DEFAULTS))
    return parser.parse_args()


def iter_tasks() -> list[dict]:
    tasks: list[dict] = []
    for path in sorted(TASKS_ROOT.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = path.relative_to(REPO_ROOT).as_posix()
        tasks.append(payload)
    return tasks


def load_changed_files(path: str | None) -> list[str]:
    if not path:
        return []
    raw = pathlib.Path(path).read_text(encoding="utf-8") if pathlib.Path(path).exists() else ""
    return [line.strip() for line in raw.splitlines() if line.strip()]


def impacted_agents(changed_files: Iterable[str]) -> set[str]:
    aliases: set[str] = set()
    for changed in changed_files:
        changed_path = pathlib.PurePosixPath(changed)
        if changed.startswith("claudecfg/agents/"):
            alias = AGENT_FILE_TO_ALIAS.get(changed_path.name)
            if alias:
                aliases.add(alias)
        if changed.startswith("claudecfg/skills/"):
            alias = SKILL_TO_ALIAS.get(changed_path.name)
            if alias:
                aliases.add(alias)
    return aliases


def impacted_fixtures(changed_files: Iterable[str]) -> set[str]:
    fixtures: set[str] = set()
    for changed in changed_files:
        parts = pathlib.PurePosixPath(changed).parts
        if len(parts) >= 3 and parts[0] == "bench" and parts[1] == "fixtures":
            fixtures.add(parts[2])
    return fixtures


def changed_task_paths(changed_files: Iterable[str]) -> set[str]:
    return {changed for changed in changed_files if changed.startswith("bench/tasks/")}


def is_global_behavior_change(changed_files: Iterable[str]) -> bool:
    for changed in changed_files:
        if changed in GLOBAL_BEHAVIOR_FILES:
            return True
        if changed.startswith(GLOBAL_BEHAVIOR_PREFIXES):
            return True
    return False


def task_overlap_key(task: dict) -> str | None:
    key = task.get("overlap_key")
    if isinstance(key, str) and key.strip():
        return key.strip()
    return None


def dedupe_tasks(tasks: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for task in tasks:
        task_path = str(task["_path"])
        if task_path in seen:
            continue
        seen.add(task_path)
        deduped.append(task)
    return deduped


def select_tasks(
    tasks: list[dict],
    suite: str,
    changed_files: list[str],
    selection_mode: str,
    *,
    exclude_overlap_with_suite: str | None = None,
) -> tuple[list[dict], list[str]]:
    suite_tasks = [task for task in tasks if task.get("suite") == suite]
    reasons: list[str] = []

    if selection_mode == "all":
        reasons.append("manual_all")
        selected = suite_tasks
    else:
        task_path_hits = changed_task_paths(changed_files)
        fixtures = impacted_fixtures(changed_files)
        agents = impacted_agents(changed_files)
        global_behavior = is_global_behavior_change(changed_files)

        selected: list[dict] = []

        if global_behavior:
            reasons.append("global_behavior_change")
            selected = suite_tasks
        else:
            for task in suite_tasks:
                task_path = str(task["_path"])
                related_agents = set(task.get("related_agents", []))
                fixture = str(task.get("fixture", "") or "")

                if task_path in task_path_hits:
                    selected.append(task)
                    continue
                if fixture and fixture in fixtures:
                    selected.append(task)
                    continue
                if agents and related_agents.intersection(agents):
                    selected.append(task)
                    continue

        if task_path_hits:
            reasons.append("task_file_change")
        if fixtures:
            reasons.append("fixture_change")
        if agents:
            reasons.append("agent_or_skill_change")

    selected = dedupe_tasks(selected)

    if exclude_overlap_with_suite and exclude_overlap_with_suite != suite and selected:
        overlapping_tasks, _ = select_tasks(
            tasks,
            exclude_overlap_with_suite,
            changed_files,
            selection_mode,
        )
        overlap_keys = {
            key
            for key in (task_overlap_key(task) for task in overlapping_tasks)
            if key
        }
        if overlap_keys:
            filtered = [task for task in selected if task_overlap_key(task) not in overlap_keys]
            if len(filtered) != len(selected):
                selected = filtered
                reasons.append(f"overlap_excluded:{exclude_overlap_with_suite}")

    return selected, reasons


def format_label(selected: list[dict], suite: str) -> str:
    if not selected:
        return ""
    if len(selected) == len([task for task in iter_tasks() if task.get("suite") == suite]):
        return SUITE_DEFAULTS[suite]
    ids = [str(task["id"]) for task in selected]
    if len(ids) <= 4:
        return ", ".join(ids)
    return ", ".join(ids[:4]) + f", +{len(ids) - 4} more"


def write_github_output(selected: list[dict], reasons: list[str], suite: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print(json.dumps({
            "suite": suite,
            "should_run": bool(selected),
            "task_files": [task["_path"] for task in selected],
            "task_ids": [task["id"] for task in selected],
            "selection_reason": ",".join(reasons) if reasons else "no_matching_changes",
        }, indent=2))
        return

    suite_task_count = len([task for task in iter_tasks() if task.get("suite") == suite])
    label = SUITE_DEFAULTS[suite] if selected and len(selected) == suite_task_count else format_label(selected, suite)
    task_lines = "\n".join(str(task["_path"]) for task in selected)
    task_ids = ",".join(str(task["id"]) for task in selected)
    reason = ",".join(reasons) if reasons else "no_matching_changes"

    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"should_run={'true' if selected else 'false'}\n")
        handle.write(f"selection_reason={reason}\n")
        handle.write(f"task_count={len(selected)}\n")
        handle.write(f"task_label={label}\n")
        handle.write(f"task_ids={task_ids}\n")
        handle.write("task_files<<__TASKS__\n")
        if task_lines:
            handle.write(task_lines + "\n")
        handle.write("__TASKS__\n")


def main() -> None:
    args = parse_args()
    tasks = iter_tasks()
    changed_files = load_changed_files(args.changed_files_file)
    selected, reasons = select_tasks(
        tasks,
        args.suite,
        changed_files,
        args.selection_mode,
        exclude_overlap_with_suite=args.exclude_overlap_with_suite,
    )
    write_github_output(selected, reasons, args.suite)


if __name__ == "__main__":
    main()
