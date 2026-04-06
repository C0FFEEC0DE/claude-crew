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
    previous_summary=None,
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
        previous_summary=previous_summary,
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
    assert "feature-weighted-average" in selected_ids


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
    assert "feature-weighted-average" not in selected_ids


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
        ["bench/fixtures/python-math/calculator.py"],
    )

    assert "fixture_change" in reasons
    assert selected_ids == {
        "bugfix-zero-division",
        "feature-weighted-average",
        "feature-manager-no-agent-choice",
        "manager-architect-tester-reviewer-weighted-average",
        "manager-bugbuster-tester-reviewer-zero-division",
        "manager-debugger-tester-reviewer-zero-division",
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


def test_resume_selects_unresolved_tasks_from_previous_summary():
    selector = load_selector_module()
    previous_summary = {
        "tasks": [
            {"task_id": "bugfix-zero-division-lite", "status": "failed"},
            {"task_id": "docs-quickstart-clarity-lite", "status": "not-run"},
            {"task_id": "refactor-report-formatting-lite", "status": "passed"},
        ]
    }

    selected_ids, reasons = select_ids(
        selector,
        "smoke",
        [],
        selection_mode="resume",
        previous_summary=previous_summary,
    )

    assert reasons == ["resume_previous_unresolved"]
    assert selected_ids == {
        "bugfix-zero-division-lite",
        "docs-quickstart-clarity-lite",
    }


def test_resume_unions_previous_unresolved_with_changed_files():
    selector = load_selector_module()
    previous_summary = {
        "tasks": [
            {"task_id": "bugfix-zero-division-lite", "status": "failed"},
            {"task_id": "docs-quickstart-clarity-lite", "status": "passed"},
            {"task_id": "refactor-report-formatting-lite", "status": "passed"},
        ]
    }

    selected_ids, reasons = select_ids(
        selector,
        "smoke",
        ["bench/fixtures/text-report/reporter.py"],
        selection_mode="resume",
        previous_summary=previous_summary,
    )

    assert "resume_previous_unresolved" in reasons
    assert "fixture_change" in reasons
    assert selected_ids == {
        "bugfix-zero-division-lite",
        "docs-quickstart-clarity-lite",
        "refactor-report-formatting-lite",
    }


def test_resume_global_behavior_change_overrides_previous_summary():
    selector = load_selector_module()
    previous_summary = {
        "tasks": [
            {"task_id": "bugfix-zero-division-lite", "status": "failed"},
            {"task_id": "docs-quickstart-clarity-lite", "status": "not-run"},
        ]
    }

    selected_ids, reasons = select_ids(
        selector,
        "smoke",
        [".github/workflows/behavior-benchmark.yml"],
        selection_mode="resume",
        previous_summary=previous_summary,
    )

    assert reasons == ["global_behavior_change"]
    assert selected_ids == {
        "bugfix-zero-division-lite",
        "docs-quickstart-clarity-lite",
        "refactor-report-formatting-lite",
    }


def test_resume_selects_unexecuted_tasks_from_previous_summary_lists():
    selector = load_selector_module()
    previous_summary = {
        "unresolved_task_ids": ["docs-quickstart-clarity-lite"],
        "unresolved_task_paths": ["bench/tasks/smoke/refactor-report-formatting-lite.json"],
        "tasks": [
            {"task_id": "bugfix-zero-division-lite", "status": "passed"},
        ],
    }

    selected_ids, reasons = select_ids(
        selector,
        "smoke",
        [],
        selection_mode="resume",
        previous_summary=previous_summary,
    )

    assert reasons == ["resume_previous_unresolved"]
    assert selected_ids == {
        "docs-quickstart-clarity-lite",
        "refactor-report-formatting-lite",
    }


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
        "feature-weighted-average",
        "feature-report-summary-line",
        "feature-manager-no-agent-choice",
        "manager-bugbuster-tester-reviewer-zero-division",
        "manager-explorer-reviewer-code-map",
        "manager-architect-tester-reviewer-weighted-average",
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

    # Both smoke and golden tasks should rely on required_used_agents for role assertion
    assert smoke_task["required_used_agents"] == ["bug"]
    assert golden_task["required_used_agents"] == ["bug"]

    # Smoke task uses simplified patterns (model-independent footer markers only)
    assert "Outcome:" in smoke_task["required_transcript_patterns"]
    assert "Changed files:|No files changed:" in smoke_task["required_transcript_patterns"]
    assert "Verification status:" in smoke_task["required_transcript_patterns"]
    # Smoke task should NOT have model-dependent patterns
    assert not any("Task:" in p for p in smoke_task["required_transcript_patterns"])

    # Golden task keeps stricter patterns for regression testing
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


def test_impacted_agents_returns_alias_for_agent_file():
    selector = load_selector_module()
    result = selector.impacted_agents(["claudecfg/agents/bug.md"])
    assert "bug" in result


def test_impacted_agents_returns_alias_for_skill_file():
    selector = load_selector_module()
    result = selector.impacted_agents(["claudecfg/skills/review.md"])
    assert "cr" in result


def test_impacted_agents_handles_multiple_changed_files():
    selector = load_selector_module()
    result = selector.impacted_agents([
        "claudecfg/agents/docwriter.md",
        "claudecfg/agents/architect.md",
    ])
    assert "doc" in result
    assert "a" in result


def test_impacted_agents_ignores_unrelated_files():
    selector = load_selector_module()
    result = selector.impacted_agents(["README.md", ".github/workflows/ci.yml"])
    assert result == set()


def test_changed_task_paths_filters_task_paths():
    selector = load_selector_module()
    result = selector.changed_task_paths([
        "README.md",
        "bench/tasks/smoke/test-task.json",
        "scripts/helper.sh",
        "bench/tasks/full/feature-x.json",
    ])
    assert result == {
        "bench/tasks/smoke/test-task.json",
        "bench/tasks/full/feature-x.json",
    }


def test_changed_task_paths_empty_input():
    selector = load_selector_module()
    assert selector.changed_task_paths([]) == set()


def test_dedupe_tasks_removes_duplicates():
    selector = load_selector_module()
    # dedupe_tasks relies on _path being set on each task dict
    task_a = {"id": "task-a", "_path": "bench/tasks/smoke/a.json"}
    task_b = {"id": "task-b", "_path": "bench/tasks/smoke/b.json"}
    task_a_dup = {"id": "task-a", "_path": "bench/tasks/smoke/a.json"}
    result = selector.dedupe_tasks([task_a, task_b, task_a_dup])
    assert len(result) == 2
    assert {t["id"] for t in result} == {"task-a", "task-b"}


def test_docs_tasks_have_minimal_fixture_readmes():
    """
    Validate that docs_required tasks have fixtures where README.md needs updating.
    This catches task/fixture misalignment where fixture already has quickstart content.
    """
    repo_root = Path(__file__).resolve().parents[2]

    # Quickstart content patterns that indicate fixture already has docs
    quickstart_patterns = [
        "npm test",
        "pytest -q",
        "quickstart",
        "## Usage",
        "## Getting Started",
    ]

    # Check all docs_required tasks
    for task_path in repo_root.glob("bench/tasks/**/*.json"):
        task = json.loads(task_path.read_text(encoding="utf-8"))

        if not task.get("docs_required", False):
            continue

        fixture_name = task.get("fixture")
        if not fixture_name:
            continue

        fixture_readme = repo_root / "bench" / "fixtures" / fixture_name / "README.md"
        if not fixture_readme.exists():
            continue

        readme_content = fixture_readme.read_text(encoding="utf-8")

        # Task ID for error messages
        task_id = task.get("id", str(task_path))

        # Check if fixture README already has quickstart content
        for pattern in quickstart_patterns:
            if pattern.lower() in readme_content.lower():
                # Allow if task is about adding something different
                # Check if task prompt mentions the existing content
                prompt = task.get("prompt", "")
                if pattern.lower() in prompt.lower():
                    # Task explicitly mentions this content, it's OK
                    continue

                # Check if this is a quickstart addition task
                if "quickstart" in prompt.lower() or "npm test" in prompt.lower():
                    raise AssertionError(
                        f"Task/fixture misalignment: {task_id}\n"
                        f"Task requires docs update but fixture README already contains '{pattern}'\n"
                        f"Fixture: {fixture_readme}\n"
                        f"Fix: Reset fixture README to minimal state or change task"
                    )
