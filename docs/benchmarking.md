# Behavioral Benchmarking

This repository has two benchmark paths:

- `scripts/bench_runner_openrouter.py` — legacy one-shot worker for cheap baseline experiments
- `scripts/bench_runner_claude_code.py` — the primary real Claude Code benchmark runner that executes `claude -p` inside isolated fixture repositories

If you want to know whether the installed profile actually works as a coding agent, use the real Claude Code path. GitHub Actions exposes that live path as separate smoke, full-suite, and subagent benchmark workflows.

## What It Checks

The behavioral benchmark copies each fixture from `bench/fixtures/` into a temporary task workdir, runs the benchmark task selected by `task_glob`, and then evaluates the outcome.

Current task assertions include:

- workspace changes were actually made
- verification-required tasks still pass the fixture-appropriate test command such as `pytest -q`, `npm test`, `cargo test`, or `go test ./...`
- implementation tasks verify the final Claude response includes exact stop-safe summary lines for `Verification status:`, `Review outcome:`, `Changed files:` or `No files changed:`, and `Remaining risks:`
- transcript-sensitive tasks verify handoff markers only when the benchmark is explicitly about stable output shape
- workflow-combination tasks prefer `required_used_agents` and `required_used_agent_groups` so CI checks which specialist roles actually ran instead of brittle `Task:` headings
- role-sensitive tasks resolve actual subagent usage from `SubagentStart` and recorded handoff lines in the debug log
- docs-required tasks changed documentation
- docs-only tasks did not change non-doc files

This makes the benchmark a behavioral acceptance gate, not just a process smoke test.

The live GitHub smoke workflow now defaults to the cheaper suite in `bench/tasks/smoke/*.json` so it can run on smaller models without turning every PR into a long provider soak:

- implement a small bugfix end to end
- keep a docs-only task out of runtime code
- preserve behavior during a bounded refactor
- run `pytest -q` when code changed
- finish with the required stop-safe summary or subagent handoff footer

The broader workflow-combination suite now lives in `bench/tasks/full/*.json`, while subagent coverage is split between `bench/tasks/subagents/smoke/*.json` and `bench/tasks/subagents/golden/*.json`. That split keeps PR coverage cheap while still preserving full role and orchestration coverage in the heavier suites.
The broader matrix still includes mixed-language fixtures such as `bench/fixtures/node-app`, so the benchmark can cover non-Python verification without forcing the default PR path to grow.

The runner invokes Claude Code with `--permission-mode acceptEdits` so isolated fixture repositories can be modified non-interactively during CI. The bundled profile allows the relevant fixture-local test commands directly, including `pytest`, `npm`, `cargo`, and `go`, so harmless verification runs do not inflate `permission_denials_count`. If a task still fails, inspect `claude_subtype`, `claude_stop_reason`, `permission_denials_count`, and `first_permission_denial` in the task summary and `result.json`.
The GitHub smoke workflow default is `8` turns per task so CI stays bounded for small models; raise it manually in `workflow_dispatch` when you want a slower debug run.
The runner also injects an explicit workflow override into the prompt so bugfix, feature, refactor, and docs tasks are not misclassified as review-only work just because the final summary must mention review outcome.
Manager-led tasks are expected to continue orchestration after manager activation unless the prompt explicitly asks for plan-only behavior. The benchmark contract now expects an early specialist handoff rather than prolonged manager-only analysis.
Parallel same-role handoffs are allowed when the manager gives them distinct scopes; benchmarks should treat that as an orchestration optimization, not as extra required role coverage.
The benchmark prompt now requires the final response to end with the exact hook-recognized summary lines for the relevant workflow. For main implementation tasks that means `Verification status:`, `Review outcome:`, `Changed files:` or `No files changed:`, and `Remaining risks:`. For subagent-oriented tasks it means `Outcome:`, `Changed files:` or `No files changed:`, `Verification status:`, and one closure line: `Remaining risks:` or `Next step:`. If the model omits required main-task summary lines, the runner performs up to `5` footer-only repair retries and then synthesizes a conservative footer from the known verification facts as a last resort.
The shell stop guards now fall back to the benchmark session transcript when a runtime omits `last_assistant_message` from `Stop` or `SubagentStop` payloads, so valid summaries are still recognized in live CI runs.
The benchmark runner now mirrors that fallback for Claude CLI results: if `.result` is empty but the session transcript contains a valid multiline summary, the task can still pass. If Claude hits the wall-clock timeout after already leaving correct workspace changes behind and the post-run checks confirm tests, docs, and required summaries, the runner records `timeout_recovered=true` and keeps the task green instead of failing on `exit_code=124` alone. GitHub CI also enables fail-fast, so the live benchmark stops after the first failed task instead of burning time on the rest of the matrix. The summary reports both `configured_tasks` and `executed_tasks`, so truncated runs are not mistaken for full-suite coverage. The live workflow currently gives each task up to `300` seconds of wall-clock runtime before the runner times it out, and `workflow_dispatch` can override that with `timeout_seconds`.
The live workflow also caps Claude Code with `CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024` by default, which keeps Ollama Cloud requests smaller and faster for benchmark runs; override it with `BEHAVIOR_BENCHMARK_MAX_OUTPUT_TOKENS` or the `workflow_dispatch` input when you need a larger response budget. If Ollama Cloud still rejects a request with a `402` affordability error, the Claude benchmark runner automatically retries with a lower output-token budget derived from the provider error before failing the task. The runner also retries short-lived upstream provider errors such as broken tool-call envelopes before giving up on the task.
Recovery metrics such as `recovered_tasks`, `timeout_recovered`, `max_turns_recovered`, and `summary_repaired` are always written into `summary.json` and surfaced in the GitHub step summary. By default they are report-only signals so the pipeline stays focused on profile behavior rather than model variance. They become hard gates only when strict caps are provided explicitly through repository variables or `workflow_dispatch` inputs.
The benchmark harness now bootstraps `~/.claude/`, `~/.claude/state/`, and `~/.claude/logs/` before live runs so Claude Code does not spend benchmark turns recreating missing home-state directories or emit avoidable ENOENT noise in CI logs. It also mirrors the installed Claude profile into each fixture workdir when available, so task-local config resolution matches the live repository setup more closely. Root-level read-only tool calls such as `Read(.)`, `Glob(.)`, and `Grep(.)` are allowed so models do not waste turns on harmless repository scans.
Benchmark tasks may also declare `forbidden_doc_patterns`; the runner scans changed documentation files and fails the task if the edited docs mention forbidden hallucinated paths or commands. Those patterns should target invented commands themselves, not negative statements that say an install or clone step is unnecessary.
Benchmark tasks may also declare `forbidden_transcript_patterns`; the runner scans the Claude session transcript and fails the task if those patterns appear anywhere in the interaction. This is useful for catching orchestration regressions such as asking the user to choose mandatory subagents instead of selecting them automatically.
Benchmark tasks may also declare `required_transcript_patterns`; the runner scans assistant/result transcript entries and fails the task if those regexes never appear. This is useful when the benchmark is specifically about a stable handoff shape or review/debug/testing structure without matching the user prompt itself.
Benchmark tasks may also declare `required_used_agents` and `required_used_agent_groups`; the runner parses actual `SubagentStart` and recorded handoff lines from the effective debug log of the attempt that produced the final result and fails the task if the expected role usage never happened. Use this for workflow-combination, docs, or manager-led orchestration workflows where the right behavioral signal is "which role actually ran", not "did the final visible reply preserve one exact heading block".
The repository validator now requires every subagent task to declare at least one required-behavior assertion through transcript patterns or used-agent expectations. If a subagent task still relies on transcript requirements, validation also enforces the shared footer-marker subset so those regexes do not drift away from the hook contract.
For prompt-behavior regressions, keep a reusable forbidden pattern set in [`../bench/patterns/forbidden-meta-chatter.json`](../bench/patterns/forbidden-meta-chatter.json). Use it to block internal-enforcement leakage such as `I see the issue`, `prefix match`, `shell guard`, or other footer-repair chatter from appearing in assistant output. The runner evaluates forbidden transcript patterns against assistant-like transcript entries only, so user prompts quoting those phrases do not create false failures.

Recommended transcript regression coverage:

- `@e` exploration task: require structural mapping output and forbid footer-repair chatter
- `@m` coordination task: require planning/coordinating output and forbid hook-mechanics chatter
- `@cr` review task: require findings output and forbid guard/prefix/meta formatting chatter

Additional focused suites can live under nested globs such as:

- `bench/tasks/subagents/smoke/*.json` for short per-role canaries
- `bench/tasks/subagents/golden/*.json` for stricter per-role regressions
- `bench/tasks/full/*.json` for multi-role workflow combinations

The subagent smoke suite under `bench/tasks/subagents/smoke/*.json` keeps one short canary task per canonical alias for PR-time coverage. The golden suite under `bench/tasks/subagents/golden/*.json` keeps one stricter regression task per alias for scheduled and manual coverage. Tasks that still validate transcript shape are expected to carry the shared footer markers `Outcome:`, `Changed files:` or `No files changed:`, `Verification status:`, and `Remaining risks:` or `Next step:` so role prompts, hook contracts, and runner assertions stay aligned.

## Hook Test Layers

Hook behavior is covered by two local harness modes:

- `bash scripts/test-hooks.sh` runs `tests/hooks/cases.json` and checks isolated hook contracts one event at a time.
- `bash scripts/test-hooks.sh tests/hooks/scenarios.json` runs shared-state scenarios that chain multiple hooks through a single session `HOME`.

Use cases for edge payloads, null/empty field handling, and single-hook contracts. Use scenarios for end-to-end flows such as prompt classification -> edit tracking -> verification -> completion, plus session lifecycle logging.

## GitHub Workflow

The behavioral benchmark workflows are:

- `.github/workflows/behavior-benchmark.yml`
- `.github/workflows/behavior-benchmark-full.yml`
- `.github/workflows/behavior-benchmark-subagents-smoke.yml`
- `.github/workflows/benchmark-nightly.yml`

`behavior-benchmark.yml`:

1. installs the Claude Code CLI
2. runs `./install.sh` so CI uses the same repo installer as local setup
3. copies the repository `.claude/` directory into each isolated fixture workdir so project-local config is exercised during the benchmark
4. collects the PR diff and maps it to affected agents, fixtures, task files, and shared workflow logic
5. selects the impacted tasks from `bench/tasks/smoke/*.json`
6. runs `scripts/run-benchmark.sh` in `command` mode with the selected task list
7. uses `scripts/bench_runner_claude_code.py` as the per-task runner
8. uploads per-task Claude artifacts plus `summary.json`
9. fails the workflow unless every selected benchmark task passes

It only runs on PRs when benchmark-relevant files changed, which keeps the live smoke path from re-running on unrelated pushes.
Agent and slash-skill changes are mapped through the frontmatter declared in `claudecfg/agents/*.md` and `claudecfg/skills/*.md`, so full-name files like `manager.md` and skill files like `review.md` stay aligned with the canonical role aliases used by the task metadata.

`behavior-benchmark-subagents-smoke.yml`:

1. runs on PRs when benchmark-relevant files changed
2. maps changed agent, skill, fixture, and workflow files to the affected subagent canaries
3. runs the selected tasks from `bench/tasks/subagents/smoke/*.json`
4. supports manual `workflow_dispatch` for on-demand checks

`behavior-benchmark-full.yml`:

1. runs on benchmark-relevant PRs, every night at `01:30 UTC`, and via manual dispatch
2. maps changed agents to related multi-role workflow tasks
3. selects only impacted tasks from `bench/tasks/full/*.json` on PRs and scheduled runs
4. on PRs, excludes full tasks whose `overlap_key` is already covered by the smoke suite selected from the same diff, so CI does not pay twice for the same bugfix/docs/refactor scenario
5. keeps those overlapping tasks in scheduled and manual full runs, so nightly/manual coverage remains complete
6. skips the scheduled job when there were no relevant changes in the recent lookback window
7. supports manual `workflow_dispatch` so the full suite can be launched on `main` without waiting for cron, or narrowed to changed-only selection when debugging; changed-only dispatch compares the current branch to `main`, and falls back to the recent lookback window when you dispatch directly on `main`

`benchmark-nightly.yml`:

1. runs every night at `01:30 UTC`
2. maps recent relevant changes to the affected golden role regressions
3. skips the scheduled job when there were no relevant changes in the recent lookback window
4. still supports change-targeted or all-task runs through `workflow_dispatch`; the changed-only manual path compares the current branch to `main`, and falls back to the recent lookback window when dispatched on `main`
5. runs tasks from `bench/tasks/subagents/golden/*.json`

## Slot-Gate Mechanism

Concurrent benchmark runs are limited by a two-slot gate enforced through `scripts/wait-for-benchmark-slot.py`. This prevents the nightly and golden suites from overloading shared CI runners when multiple workflow dispatches or cron jobs fire simultaneously.

**How it works:**

- `wait-for-benchmark-slot.py` polls a dedicated GitHub API endpoint (or a comparable availability check) until a slot opens, or exits immediately if one is already free.
- The gate allows a maximum of **2 concurrent benchmark runs** at any time.
- When the gate is occupied, the script waits and retries at a fixed interval until a slot becomes available.

**Rate-limit handling:**

- If the slot check returns HTTP 403, the script reads the `Retry-After` header and sleeps for the requested interval before retrying.
- This handles GitHub API secondary-rate-limit errors gracefully without burning CI minutes on tight polling loops.

**Nightly and golden suites use this gate automatically** — both `benchmark-nightly.yml` and any manual dispatch of the golden suite invoke `wait-for-benchmark-slot.py` before launching tasks.

**Log rotation for notification telemetry:**

Notification hooks write session events to `~/.claude/logs/notification.jsonl`. To prevent unbounded log growth on long-running CI runners, the hook installation step rotates existing logs: if `notification.jsonl` exceeds a configured size threshold, the file is renamed with a timestamp suffix and a fresh log is started. The rotation threshold is set in the hook configuration in `claudecfg/hooks/notification.sh`.

## Required GitHub Setup

Repository settings:

1. `Settings -> Secrets and variables -> Actions -> New repository secret`
2. Add `OLLAMA_API_KEY`
3. `Settings -> Secrets and variables -> Actions -> Variables`
4. Add `OLLAMA_MODEL` as the general fallback provider model
5. Optionally add `BEHAVIOR_BENCHMARK_MODEL` to pin a separate model for benchmark CI without changing the wider repository default
6. Optionally add `BEHAVIOR_BENCHMARK_TIMEOUT_SECONDS` to override the benchmark per-task timeout
7. Optionally add `BEHAVIOR_BENCHMARK_MAX_OUTPUT_TOKENS` to override the Claude Code output-token cap
8. Optionally add `BEHAVIOR_BENCHMARK_MAX_RECOVERED_TASKS` to enable strict gating on recovered tasks
9. Optionally add `BEHAVIOR_BENCHMARK_MAX_SUMMARY_REPAIRED_TASKS` to enable strict gating on summary-repaired tasks

Required benchmark model:

```text
qwen3.5:cloud
```

Recommended benchmark timeout:

```text
300
```

Recommended benchmark max output tokens:

```text
1024
```

Strict mode is opt-in. Leave the recovery-cap variables unset if you want recovered tasks to remain informational only.

## Local Usage

With Claude Code CLI and Ollama Cloud env vars available:

```bash
export OLLAMA_API_KEY=...
export ANTHROPIC_BASE_URL=https://ollama.com
export ANTHROPIC_AUTH_TOKEN="$OLLAMA_API_KEY"
export ANTHROPIC_API_KEY=
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:cloud}"
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-1024}"
export BENCH_RUNNER_CMD="python3 scripts/bench_runner_claude_code.py"
bash scripts/run-benchmark.sh --output-dir /tmp/claude-bench --mode command
bash scripts/assert-benchmark-summary.sh /tmp/claude-bench/summary.json
```

To run the broader workflow-combination suite manually:

```bash
bash scripts/run-benchmark.sh --output-dir /tmp/claude-bench-full --mode command --task-glob 'bench/tasks/full/*.json'
```

To run the smoke or golden subagent suites manually:

```bash
bash scripts/run-benchmark.sh --output-dir /tmp/claude-bench-subagents-smoke --mode command --task-glob 'bench/tasks/subagents/smoke/*.json'
bash scripts/run-benchmark.sh --output-dir /tmp/claude-bench-subagents-golden --mode command --task-glob 'bench/tasks/subagents/golden/*.json'
```

For cheap synthetic checks without the real agent:

```bash
bash scripts/run-benchmark.sh --output-dir /tmp/claude-bench-mock --mode mock
```

## Output Artifacts

Each task directory contains:

- `result.json`
- `task-prompt.txt`
- `task-summary.txt`
- `claude-result.json`
- `claude-result.txt`
- `claude-debug.log`
- `claude-stderr.log`
- `workspace.patch`
- `changed-files.json`

The benchmark root contains:

- `summary.json`
- `benchmark-report.md`

Use `summary.json` as the machine-readable gate and `benchmark-report.md` as the human-readable markdown report with overview and per-task status tables. The per-task artifacts remain the debugging source for failures.
The workflow log now prints task metadata, model, workdir, prompt excerpt, raw Claude JSON excerpt, parsed failure reasons, debug log excerpt, verification output, patch excerpt, full `result.json` for each task, and the rendered markdown report table.
