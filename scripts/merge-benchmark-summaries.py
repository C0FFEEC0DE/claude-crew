#!/usr/bin/env python3

import argparse
import json
import pathlib
from datetime import datetime, UTC


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("summary_files", nargs="+")
    return parser.parse_args()


def median(values: list[float]) -> float:
    if not values:
        return 0
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2


def rate(num: int, den: int) -> float:
    if den == 0:
        return 0
    return num / den


def merge_summaries(summary_payloads: list[dict]) -> dict:
    if not summary_payloads:
        raise ValueError("at least one summary is required")

    first = summary_payloads[0]
    tasks = []
    configured_tasks = 0
    executed_tasks = 0
    for payload in summary_payloads:
        configured_tasks += int(payload["totals"]["configured_tasks"])
        executed_tasks += int(payload["totals"]["executed_tasks"])
        tasks.extend(payload.get("tasks", []))

    total = len(tasks)
    passed = len([task for task in tasks if task["status"] == "passed"])
    clean_passed = len(
        [
            task
            for task in tasks
            if task["status"] == "passed"
            and task.get("recovered_nonzero_exit") is not True
            and (task.get("summary_repaired_by") or "none") == "none"
        ]
    )
    completed = len([task for task in tasks if task.get("completed") is True])
    verification_required = len([task for task in tasks if task.get("verification_required") is True])
    tests_run = len([task for task in tasks if task.get("tests_run") is True])
    tests_passed = len([task for task in tasks if task.get("tests_passed") is True])
    review_required = len([task for task in tasks if task.get("review_required") is True])
    review_present = len([task for task in tasks if task.get("review_present") is True])
    docs_required = len([task for task in tasks if task.get("docs_required") is True])
    docs_updated = len([task for task in tasks if task.get("docs_updated") is True])
    recovered_tasks = len([task for task in tasks if task.get("recovered_nonzero_exit") is True])
    timeout_recovered = len([task for task in tasks if task.get("timeout_recovered") is True])
    max_turns_recovered = len([task for task in tasks if task.get("max_turns_recovered") is True])
    summary_repaired = len([task for task in tasks if (task.get("summary_repaired_by") or "none") != "none"])
    policy_violations = sum(int(task.get("policy_violations", 0)) for task in tasks)
    tool_failures = sum(int(task.get("tool_failures", 0)) for task in tasks)

    return {
        "schema_version": first["schema_version"],
        "mode": first["mode"],
        "runner": first["runner"],
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_ref": first["source_ref"],
        "source_sha": first["source_sha"],
        "task_glob": first["task_glob"],
        "totals": {
            "configured_tasks": configured_tasks,
            "executed_tasks": executed_tasks,
            "tasks": executed_tasks,
            "passed": passed,
            "clean_passed": clean_passed,
            "completed": completed,
            "verification_required": verification_required,
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "review_required": review_required,
            "review_present": review_present,
            "docs_required": docs_required,
            "docs_updated": docs_updated,
            "recovered_tasks": recovered_tasks,
            "timeout_recovered": timeout_recovered,
            "max_turns_recovered": max_turns_recovered,
            "summary_repaired": summary_repaired,
            "policy_violations": policy_violations,
            "tool_failures": tool_failures,
        },
        "rates": {
            "task_pass_rate": rate(passed, total),
            "clean_pass_rate": rate(clean_passed, total),
            "completion_rate": rate(completed, total),
            "verification_rate": rate(len([task for task in tasks if (task.get("verification_required") is False) or (task.get("tests_run") is True)]), total),
            "verification_pass_rate": rate(len([task for task in tasks if (task.get("verification_required") is False) or (task.get("tests_passed") is True)]), total),
            "review_compliance_rate": rate(len([task for task in tasks if (task.get("review_required") is False) or (task.get("review_present") is True)]), total),
            "docs_compliance_rate": rate(len([task for task in tasks if (task.get("docs_required") is False) or (task.get("docs_updated") is True)]), total),
            "recovered_task_rate": rate(recovered_tasks, total),
            "summary_repair_rate": rate(summary_repaired, total),
            "execution_coverage_rate": rate(executed_tasks, configured_tasks),
        },
        "median_runtime_seconds": median([float(task["runtime_seconds"]) for task in tasks]),
        "tasks": tasks,
    }


def main() -> None:
    args = parse_args()
    payloads = [
        json.loads(pathlib.Path(summary_file).read_text(encoding="utf-8"))
        for summary_file in args.summary_files
    ]
    merged = merge_summaries(payloads)
    pathlib.Path(args.output).write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
