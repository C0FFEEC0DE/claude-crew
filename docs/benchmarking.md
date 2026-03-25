# Benchmarking

This repository now separates four kinds of signal:

- structural validity
- hook behavior correctness
- benchmarked agent outcomes
- manual real-Claude-Code runs via OpenRouter

## Workflows

### Validate

Workflow: `.github/workflows/validate.yml`

Purpose:

- validate JSON
- validate shell syntax
- validate agent frontmatter
- validate benchmark metadata and hook case manifests
- catch whitespace and patch formatting issues

### Hook Tests

Workflow: `.github/workflows/hooks-test.yml`

Purpose:

- run deterministic behavior tests against the hook scripts
- prove that state tracking and stop gates work as expected

Local entrypoint:

```bash
bash scripts/test-hooks.sh
```

### Benchmark

Workflow: `.github/workflows/benchmark.yml`

Purpose:

- compare a baseline ref against a candidate ref
- aggregate task results into `summary.json`
- compute a comparison verdict
- publish a markdown report to the job summary

Event behavior:

- `push` — runs automatically and compares the previous commit to the current commit
- `pull_request` — intentionally uses `mock` mode to avoid exposing benchmark secrets to untrusted code
- `workflow_dispatch` — lets you choose explicit baseline and candidate refs
- `schedule` — compares the previous commit to the current default-branch commit

For real measurements on push, manual runs, or the nightly schedule, configure either:

- `OPENROUTER_API_KEY` for the built-in OpenRouter runner
- `BENCH_RUNNER_CMD` for your own runner

### Real Claude Code

Workflow: `.github/workflows/real-claude-code.yml`

Purpose:

- run the official `anthropics/claude-code-action@v1`
- install the repository's `claudecfg` profile into `~/.claude`
- route Claude Code through OpenRouter
- capture the resulting workspace diff as artifacts

This workflow is manual-only by design because it uses the real Claude Code runtime and consumes paid model calls.

## OpenRouter Setup

If you already have an OpenRouter key, this is the fastest path.

Repository settings:

1. `Settings -> Secrets and variables -> Actions -> New repository secret`
2. Add `OPENROUTER_API_KEY`
3. `Settings -> Secrets and variables -> Actions -> Variables`
4. Optionally add `OPENROUTER_MODEL`

Suggested starting value for routine push benchmarking:

```text
qwen/qwen3-coder-next
```

Lower-cost but less reliable smoke-test options:

```text
qwen/qwen3-coder:free
openrouter/free
```

Free models can rate-limit aggressively, so they are usually a bad choice if you want benchmark jobs to stay green on every push.

The benchmark workflow will automatically switch to:

```text
python3 scripts/bench_runner_openrouter.py
```

when `OPENROUTER_API_KEY` is present and no custom `BENCH_RUNNER_CMD` is configured.

Minimum GitHub setup:

1. Add secret `OPENROUTER_API_KEY`
2. Add variable `OPENROUTER_MODEL`
3. Push a commit to exercise the cheap benchmark worker
4. Run `Real Claude Code` manually when you want the official Claude Code runtime

Important limitation:

- this does **not** run the real Claude Code GitHub Action
- it runs a custom benchmark worker that uses your repo instructions as prompt context
- this is good for cheap comparative benchmarking
- this is **not** a faithful test of Claude Code hooks, permissions, or multi-turn tool execution

In this repository, the real-runtime path is provided separately by `.github/workflows/real-claude-code.yml`, using OpenRouter as the Anthropic-compatible backend for the official Claude Code action.

## Runner Contract

`scripts/run-benchmark.sh` prepares each task and exports:

- `BENCH_TASK_FILE`
- `BENCH_TASK_ID`
- `BENCH_WORKDIR`
- `BENCH_FIXTURE_DIR`
- `BENCH_OUTPUT_DIR`
- `BENCH_REPO_ROOT`

Your runner command must:

1. read the task definition from `$BENCH_TASK_FILE`
2. execute the task in `$BENCH_WORKDIR`
3. write `$BENCH_OUTPUT_DIR/result.json`

## Expected `result.json`

Required fields:

```json
{
  "task_id": "feature-weighted-average",
  "status": "passed",
  "completed": true,
  "verification_required": true,
  "tests_run": true,
  "tests_passed": true,
  "review_required": true,
  "review_present": true,
  "docs_required": true,
  "docs_updated": true,
  "policy_violations": 0,
  "tool_failures": 0,
  "runtime_seconds": 32,
  "notes": "Short human-readable summary."
}
```

`bench/schema/summary.schema.json` describes the aggregated `summary.json` emitted by `scripts/run-benchmark.sh`.

## Secret Configuration

Create a repository variable or secret named `BENCH_RUNNER_CMD`.

Typical pattern:

```bash
/path/to/your/benchmark-runner.sh
```

That runner can internally call Claude Code, Codex, OpenRouter, or another agent harness, as long as it obeys the `result.json` contract.

## Related Workflows

- `.github/workflows/validate.yml` — fast structural validation on every push and PR
- `.github/workflows/hooks-test.yml` — deterministic hook behavior tests on every push and PR
- `.github/workflows/security-scan.yml` — secret scanning on every push and PR plus a weekly scheduled run
- `.github/workflows/real-claude-code.yml` — manual official Claude Code run via OpenRouter with the installed `claudecfg` profile

## Verdict Logic

`scripts/compare-benchmarks.sh` currently marks the candidate as:

- `regressed` if pass/compliance metrics drop or violations/failures increase
- `improved` if no key metric regressed and at least one metric improved
- `no_significant_change` otherwise

This is intentionally conservative. If you want stricter scoring later, evolve the task set first and only then tighten thresholds.
