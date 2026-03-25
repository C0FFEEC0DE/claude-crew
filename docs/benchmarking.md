# Benchmarking

This repository now separates three kinds of signal:

- structural validity
- hook behavior correctness
- benchmarked agent outcomes

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

On pull requests, the workflow intentionally uses `mock` mode.
That prevents benchmark secrets from being exposed to untrusted code.

For real measurements, use `workflow_dispatch` or the nightly schedule and configure either:

- `OPENROUTER_API_KEY` for the built-in OpenRouter runner
- `BENCH_RUNNER_CMD` for your own runner

## OpenRouter Setup

If you already have an OpenRouter key, this is the fastest path.

Repository settings:

1. `Settings -> Secrets and variables -> Actions -> New repository secret`
2. Add `OPENROUTER_API_KEY`
3. `Settings -> Secrets and variables -> Actions -> Variables`
4. Optionally add `OPENROUTER_MODEL`

Suggested starting value:

```text
anthropic/claude-sonnet-4.5
```

The benchmark workflow will automatically switch to:

```text
python3 scripts/bench_runner_openrouter.py
```

when `OPENROUTER_API_KEY` is present and no custom `BENCH_RUNNER_CMD` is configured.

Important limitation:

- this does **not** run the real Claude Code GitHub Action
- it runs a custom benchmark worker that uses your repo instructions as prompt context
- this is good for cheap comparative benchmarking
- this is **not** a faithful test of Claude Code hooks, permissions, or multi-turn tool execution

If you need to test the real Claude Code runtime with your configs, use Anthropic API, Bedrock, or Vertex AI with the official Claude Code Action instead.

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

## Verdict Logic

`scripts/compare-benchmarks.sh` currently marks the candidate as:

- `regressed` if pass/compliance metrics drop or violations/failures increase
- `improved` if no key metric regressed and at least one metric improved
- `no_significant_change` otherwise

This is intentionally conservative. If you want stricter scoring later, evolve the task set first and only then tighten thresholds.
