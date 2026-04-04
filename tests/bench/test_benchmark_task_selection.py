import importlib.util
import json
from pathlib import Path


def load_selector_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "select-benchmark-tasks.py"
    spec = importlib.util.spec_from_file_location("select_benchmark_tasks", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def select_ids(
    module,
    suite,
    changed_files,
    selection_mode="changed",
    exclude_overlap_with_suite=None,
    priority_profile=None,
    max_tasks=None,
):
    tasks = module.iter_tasks()
    selected, reasons = module.select_tasks(
        tasks,
        suite,
        changed_files,
        selection_mode,
        exclude_overlap_with_suites=[exclude_overlap_with_suite] if exclude_overlap_with_suite else [],
    )
    selected = module.apply_priority_profile(selected, priority_profile)
    selected = module.limit_tasks(selected, max_tasks, reasons)
    return {task["id"] for task in selected}, reasons


def test_global_workflow_change_selects_entire_smoke_suite():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "smoke",
        [".github/workflows/behavior-benchmark.yml"],
    )

    assert reasons == ["global_behavior_change"]
    assert selected_ids == {
        "bugfix-zero-division-lite",
        "docs-quickstart-clarity-lite",
        "refactor-report-formatting-lite",
    }


def test_summary_renderer_change_selects_entire_smoke_suite():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "smoke",
        ["scripts/render-benchmark-summary.sh"],
    )

    assert reasons == ["global_behavior_change"]
    assert selected_ids == {
        "bugfix-zero-division-lite",
        "docs-quickstart-clarity-lite",
        "refactor-report-formatting-lite",
    }


def test_unrelated_workflow_change_does_not_select_full_suite():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        [".github/workflows/security-scan.yml"],
    )

    assert reasons == []
    assert selected_ids == set()


def test_benchmark_workflow_change_still_selects_full_suite():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        [".github/workflows/behavior-benchmark-full.yml"],
    )

    assert reasons == ["global_behavior_change"]
    assert "manager-explorer-reviewer-code-map" in selected_ids
    assert "feature-node-app-multiply" in selected_ids


def test_agent_change_selects_related_full_workflow_tasks():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        ["claudecfg/agents/bug.md"],
    )

    assert "agent_or_skill_change" in reasons
    assert "manager-bugbuster-tester-reviewer-zero-division" in selected_ids
    assert "bugfix-zero-division" in selected_ids
    assert "feature-node-app-multiply" not in selected_ids


def test_full_name_agent_change_selects_related_full_workflow_tasks():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        ["claudecfg/agents/manager.md"],
    )

    assert "agent_or_skill_change" in reasons
    assert "manager-explorer-reviewer-code-map" in selected_ids
    assert "manager-bugbuster-tester-reviewer-zero-division" in selected_ids
    assert "bugfix-zero-division" not in selected_ids


def test_fixture_change_selects_tasks_for_that_fixture_only():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        ["bench/fixtures/node-app/src/calculator.js"],
    )

    assert "fixture_change" in reasons
    assert selected_ids == {
        "docs-node-app-quickstart",
        "feature-node-app-multiply",
        "manager-docwriter-node-quickstart",
    }


def test_full_pr_selection_excludes_tasks_already_covered_by_smoke():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        ["bench/fixtures/text-report/reporter.py"],
        exclude_overlap_with_suite="smoke",
    )

    assert "fixture_change" in reasons
    assert "overlap_excluded:smoke" in reasons
    assert "docs-quickstart-clarity" not in selected_ids
    assert "refactor-report-formatting" not in selected_ids
    assert selected_ids == {
        "feature-report-summary-line",
        "manager-explorer-reviewer-code-map",
        "manager-housekeeper-tester-reviewer-report-refactor",
    }


def test_full_task_file_change_keeps_task_when_smoke_does_not_run():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        ["bench/tasks/full/bugfix-zero-division.json"],
        exclude_overlap_with_suite="smoke",
    )

    assert "task_file_change" in reasons
    assert "overlap_excluded:smoke" not in reasons
    assert selected_ids == {"bugfix-zero-division"}


def test_subagent_smoke_agent_change_selects_only_that_role():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "subagents_smoke",
        ["claudecfg/skills/review.md"],
    )

    assert "agent_or_skill_change" in reasons
    assert selected_ids == {"subagent-code-reviewer-note-lite"}


def test_full_name_skill_mapping_selects_related_subagent_smoke_task():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "subagents_smoke",
        ["claudecfg/skills/docs.md"],
    )

    assert "agent_or_skill_change" in reasons
    assert selected_ids == {
        "subagent-architect-rollout-lite",
        "subagent-docwriter-quickstart-lite",
    }


def test_docwriter_change_also_selects_architect_doc_tasks():
    selector = load_selector_module()
    smoke_ids, smoke_reasons = select_ids(
        selector,
        "subagents_smoke",
        ["claudecfg/agents/docwriter.md"],
    )
    golden_ids, golden_reasons = select_ids(
        selector,
        "subagents_golden",
        ["claudecfg/agents/docwriter.md"],
    )

    assert smoke_reasons == ["agent_or_skill_change"]
    assert "subagent-docwriter-quickstart-lite" in smoke_ids
    assert "subagent-architect-rollout-lite" in smoke_ids
    assert golden_reasons == ["agent_or_skill_change"]
    assert "subagent-docwriter-fixture-accuracy" in golden_ids
    assert "subagent-architect-design-note" in golden_ids


def test_manual_all_returns_entire_golden_suite():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "subagents_golden",
        [],
        selection_mode="all",
    )

    assert reasons == ["manual_all"]


def test_full_pr_priority_profile_limits_global_change_to_six_tasks():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "full",
        [".github/workflows/behavior-benchmark-full.yml"],
        exclude_overlap_with_suite="smoke",
        priority_profile="pr_full",
        max_tasks=6,
    )

    assert "global_behavior_change" in reasons
    assert "task_limit:6" in reasons
    assert selected_ids == {
        "docs-node-app-quickstart",
        "feature-weighted-average",
        "feature-report-summary-line",
        "manager-bugbuster-tester-reviewer-zero-division",
        "manager-explorer-reviewer-code-map",
        "manager-docwriter-node-quickstart",
    }
    assert len(selected_ids) == 6


def test_manager_led_full_tasks_require_role_usage_assertions():
    repo_root = Path(__file__).resolve().parents[2]
    task_files = sorted((repo_root / "bench" / "tasks" / "full").glob("manager-*.json"))

    assert task_files

    for task_file in task_files:
        task = json.loads(task_file.read_text(encoding="utf-8"))
        assert task.get("required_used_agents"), f"{task_file.name} must declare required_used_agents"


def test_bugbuster_tasks_use_role_assertion_and_relaxed_findings_patterns():
    repo_root = Path(__file__).resolve().parents[2]
    smoke_task = json.loads(
        (repo_root / "bench" / "tasks" / "subagents" / "smoke" / "subagent-bugbuster-zero-division-lite.json").read_text(
            encoding="utf-8"
        )
    )
    golden_task = json.loads(
        (
            repo_root
            / "bench"
            / "tasks"
            / "subagents"
            / "golden"
            / "subagent-bugbuster-findings-regression.json"
        ).read_text(encoding="utf-8")
    )

    assert smoke_task["required_used_agents"] == ["bug"]
    assert golden_task["required_used_agents"] == ["bug"]
    assert "Findings:|Investigation" in smoke_task["required_transcript_patterns"]
    assert "Outcome:|Fix:" in smoke_task["required_transcript_patterns"]
    assert "Findings:|Investigation" in golden_task["required_transcript_patterns"]
    assert "Outcome:|Fix:" in golden_task["required_transcript_patterns"]


def test_subagent_explorer_code_map_requires_changed_files_heading():
    repo_root = Path(__file__).resolve().parents[2]
    task = json.loads(
        (
            repo_root
            / "bench"
            / "tasks"
            / "subagents"
            / "smoke"
            / "subagent-explorer-code-map-lite.json"
        ).read_text(encoding="utf-8")
    )

    assert "Changed files:|No files changed:" in task["required_transcript_patterns"]
    assert "Changed files:" in task["prompt"]


def test_manager_bugbuster_full_task_requires_linear_handoffs():
    repo_root = Path(__file__).resolve().parents[2]
    task = json.loads(
        (
            repo_root
            / "bench"
            / "tasks"
            / "full"
            / "manager-bugbuster-tester-reviewer-zero-division.json"
        ).read_text(encoding="utf-8")
    )

    assert task["required_used_agents"] == ["m", "bug", "t", "cr"]
    assert "exact order: @bug for the fix, then directly to @t" in task["prompt"]
    assert any("directly from @bug to @t to @cr" in criterion for criterion in task["success_criteria"])
