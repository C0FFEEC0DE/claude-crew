# Behavioral Benchmarking

This repository has two benchmark paths:

- `scripts/bench_runner_openrouter.py` — legacy one-shot OpenRouter worker for cheap baseline experiments
- `scripts/bench_runner_claude_code.py` — the primary real Claude Code benchmark runner that executes `claude -p` inside isolated fixture repositories

If you want to know whether the installed profile actually works as a coding agent, use the real Claude Code path. This is also the only live Claude runtime workflow in GitHub Actions.

## What It Checks

The behavioral benchmark copies each fixture from `bench/fixtures/` into a temporary task workdir, runs the benchmark task from `bench/tasks/`, and then evaluates the outcome.

Current task assertions include:

- workspace changes were actually made
- verification-required tasks still pass `pytest -q`
- the final Claude response includes:
  - `Verification status:`
  - `Review outcome:`
  - `Remaining risks:`
- docs-required tasks changed documentation
- docs-only tasks did not change non-doc files

This makes the benchmark a behavioral acceptance gate, not just a process smoke test.

## GitHub Workflow

The behavioral benchmark workflow is:

- `.github/workflows/behavior-benchmark.yml`

It:

1. installs `claudecfg/*` into `~/.claude`
2. installs the Claude Code CLI
3. runs `scripts/run-benchmark.sh` in `command` mode
4. uses `scripts/bench_runner_claude_code.py` as the per-task runner
5. uploads per-task Claude artifacts plus `summary.json`
6. fails the workflow unless every benchmark task passes

## Required GitHub Setup

Repository settings:

1. `Settings -> Secrets and variables -> Actions -> New repository secret`
2. Add `OPENROUTER_API_KEY`
3. `Settings -> Secrets and variables -> Actions -> Variables`
4. Add `OPENROUTER_MODEL`

Recommended model:

```text
nvidia/nemotron-3-super-120b-a12b:free
```

## Local Usage

With Claude Code CLI and OpenRouter env vars available:

```bash
export OPENROUTER_API_KEY=...
export ANTHROPIC_BASE_URL=https://openrouter.ai/api
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_API_KEY=
export CLAUDE_MODEL="${CLAUDE_MODEL:-nvidia/nemotron-3-super-120b-a12b:free}"
export BENCH_RUNNER_CMD="python3 scripts/bench_runner_claude_code.py"
bash scripts/run-benchmark.sh --output-dir /tmp/claude-bench --mode command
bash scripts/assert-benchmark-summary.sh /tmp/claude-bench/summary.json
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

Use `summary.json` as the machine-readable gate and the per-task artifacts for debugging failures.
The workflow log now prints task metadata, model, workdir, prompt excerpt, raw Claude JSON excerpt, parsed failure reasons, debug log excerpt, verification output, patch excerpt, and full `result.json` for each task.
