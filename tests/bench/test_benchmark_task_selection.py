import importlib.util
from pathlib import Path


def load_selector_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "select-benchmark-tasks.py"
    spec = importlib.util.spec_from_file_location("select_benchmark_tasks", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def select_ids(module, suite, changed_files, selection_mode="changed"):
    tasks = module.iter_tasks()
    selected, reasons = module.select_tasks(tasks, suite, changed_files, selection_mode)
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
    assert selected_ids == {"subagent-docwriter-quickstart-lite"}


def test_manual_all_returns_entire_golden_suite():
    selector = load_selector_module()
    selected_ids, reasons = select_ids(
        selector,
        "subagents_golden",
        [],
        selection_mode="all",
    )

    assert reasons == ["manual_all"]
    assert len(selected_ids) == 9
