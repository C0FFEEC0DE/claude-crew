import json
import subprocess
from pathlib import Path


def test_render_summary_produces_markdown_overview(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "render-benchmark-summary.sh"
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "mode": "cmd",
                "runner": "r",
                "generated_at": "2026-01-01T00:00:00Z",
                "source_ref": "ref",
                "source_sha": "sha",
                "task_glob": "g",
                "totals": {
                    "configured_tasks": 1,
                    "executed_tasks": 1,
                    "passed": 1,
                    "clean_passed": 1,
                    "completed": 1,
                    "verification_required": 0,
                    "tests_run": 0,
                    "review_required": 0,
                    "review_present": 0,
                    "docs_required": 0,
                    "docs_updated": 0,
                    "recovered_tasks": 0,
                    "timeout_recovered": 0,
                    "max_turns_recovered": 0,
                    "summary_repaired": 0,
                    "policy_violations": 0,
                    "tool_failures": 0,
                },
                "rates": {
                    "task_pass_rate": 1.0,
                    "clean_pass_rate": 1.0,
                    "completion_rate": 1.0,
                    "verification_rate": 1.0,
                    "verification_pass_rate": 1.0,
                    "review_compliance_rate": 1.0,
                    "docs_compliance_rate": 1.0,
                    "recovered_task_rate": 0.0,
                    "summary_repair_rate": 0.0,
                    "execution_coverage_rate": 1.0,
                },
                "median_runtime_seconds": 10.0,
                "tasks": [
                    {
                        "task_id": "test-task",
                        "status": "passed",
                        "completed": True,
                        "runtime_seconds": 10,
                        "verification_required": False,
                        "tests_run": False,
                        "tests_passed": False,
                        "review_required": False,
                        "review_present": True,
                        "docs_required": False,
                        "docs_updated": True,
                        "policy_violations": 0,
                        "tool_failures": 0,
                        "recovered_nonzero_exit": False,
                        "timeout_recovered": False,
                        "max_turns_recovered": False,
                        "summary_repaired_by": "none",
                        "changed_files": [],
                        "failures": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", str(script), str(summary)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "### Overview" in result.stdout
    assert "| Configured tasks | 1 |" in result.stdout
    # jq's tonumber drops trailing zeros (100.0 becomes 100), so check for "100%" not "100.0%"
    assert "| Pass rate | 100% |" in result.stdout
    assert "| `test-task`" in result.stdout  # task appears in table


def test_render_summary_zero_tasks(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "render-benchmark-summary.sh"
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "mode": "cmd",
                "runner": "r",
                "generated_at": "2026-01-01T00:00:00Z",
                "source_ref": "ref",
                "source_sha": "sha",
                "task_glob": "g",
                "totals": {
                    "configured_tasks": 0,
                    "executed_tasks": 0,
                    "passed": 0,
                    "clean_passed": 0,
                    "completed": 0,
                    "verification_required": 0,
                    "tests_run": 0,
                    "review_required": 0,
                    "review_present": 0,
                    "docs_required": 0,
                    "docs_updated": 0,
                    "recovered_tasks": 0,
                    "timeout_recovered": 0,
                    "max_turns_recovered": 0,
                    "summary_repaired": 0,
                    "policy_violations": 0,
                    "tool_failures": 0,
                },
                "rates": {
                    "task_pass_rate": 0.0,
                    "clean_pass_rate": 0.0,
                    "completion_rate": 0.0,
                    "verification_rate": 0.0,
                    "verification_pass_rate": 0.0,
                    "review_compliance_rate": 0.0,
                    "docs_compliance_rate": 0.0,
                    "recovered_task_rate": 0.0,
                    "summary_repair_rate": 0.0,
                    "execution_coverage_rate": 0.0,
                },
                "median_runtime_seconds": 0.0,
                "tasks": [],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", str(script), str(summary)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "### Overview" in result.stdout
    assert "No executed tasks" in result.stdout
