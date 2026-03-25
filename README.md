# Claude Code Configuration

Claude Code configuration with custom agents, workflows, and hook-gated SDLC.

## Quick Start

```bash
cd claudecfg
./install.sh
```

This will backup your current config and install the new one.

## Auto-Execution

In project folders (`~/projects/**`, `~/code/**`, `~/repos/**`, `~/work/**`), agents can execute safe commands automatically without confirmation.

### Safety
- Protected paths: `~/.ssh`, `~/.aws`, `/etc`, `/usr`, etc.
- Denied commands: `sudo`, `mkfs`, `dd`, `rm -rf /`
- Confirmation required outside project folders
- Release/deploy actions are intentionally out of scope for this profile

## What's Included

### Agents (9)

| Alias | Agent | Character | Purpose |
|-------|-------|-----------|---------|
| `@m` | Manager | Big Boss | Coordinates other agents |
| `@cr` | Code Reviewer | Toxic Senior | Code review + security |
| `@t` | Tester | Paranoid | Writing tests (TDD, BDD) |
| `@e` | Explorer | Nerd | Exploring code |
| `@a` | Architect | The Architect | System design + SOLID |
| `@bug` | Bugbuster | Cyber Detective | Bug hunting |
| `@dbg` | Debugger | Bug Hunter | Debugging issues |
| `@doc` | Docwriter | Wiki-Wiki | Documentation |
| `@hk` | Housekeeper | The Cleaner | Cleanup + DevOps |

Full names also work: `@manager`, `@code-reviewer`, etc.

### Slash Commands

Commands that invoke specialized agents:

- `/debug` — debugging session
- `/test` — testing session (invokes @tester)
- `/design` — design session (invokes @architect)
- `/refactor` — refactoring session (invokes @housekeeper)
- `/review` — code review (invokes @code-reviewer)
- `/docs` — documentation session (invokes @docwriter)

### Workflows

- `workflows/bugfix.md` — fix a bug
- `workflows/new-feature.md` — implement feature
- `workflows/refactor.md` — refactor code
- `workflows/security-scan.md` — scan for private data (API keys, passwords, tokens)
- `workflows/release.md` — optional manual checklist, not part of the mandatory SDLC profile

### Hooks

The profile uses hooks as enforcement points, not markdown alone:

- `SessionStart` — bootstrap SDLC context and detect test/lint/build commands
- `UserPromptSubmit` — classify task into `bugfix|feature|refactor`
- `PreToolUse` / `PermissionRequest` — block destructive or release/deploy actions
- `PostToolUse` / `PostToolUseFailure` — track edits and verification commands
- `TaskCompleted` / `Stop` / `TeammateIdle` — prevent finishing without verification
- `SessionEnd` — index transcript paths and session metadata for later dataset work

## Usage

### Call an agent directly (shortcuts)
```
@e explore the auth module
@cr review api.py
@t write tests for utils
@a design user auth
@bug find login bug
```

### Use full names
```
@explorer explore the auth module
@code-reviewer review api.py
@tester write tests for utils
```

### Use workflow (get plan)
```
@m fix bug in login
@manager implement new feature: user authentication
```

Manager can coordinate work, but completion is enforced by hooks. The expected flow is:
`discover -> design -> implement -> verify -> review -> docs when behavior changes -> cleanup`

### Use slash command
```
/debug
/test
/design
```

## Configuration

See `claudecfg/settings.json` for permissions and settings.

## CI and Benchmarks

GitHub Actions now covers three levels:

- `Validate` — fast structural checks on every push and PR
- `Hook Tests` — behavior tests for the SDLC hook scripts
- `Benchmark` — baseline vs candidate comparison with a PR/job summary

### Fast CI

`Validate` runs:

- `bash scripts/validate.sh`
- shell syntax checks for `claudecfg/hooks/*.sh` and `scripts/*.sh`
- JSON checks for settings, hook cases, and benchmark metadata
- `git diff --check`

`Hook Tests` runs:

- `bash scripts/test-hooks.sh`

This harness verifies that key hooks block dangerous commands, classify prompts correctly, record verification, and refuse completion without tests when code changed.

### Benchmarks

Benchmark task definitions live under `bench/tasks/`.
Task fixtures live under `bench/fixtures/`.
The benchmark summary schema lives in `bench/schema/summary.schema.json`.

By default, the GitHub benchmark workflow uses `mock` mode for pull requests so the pipeline stays safe for untrusted code.

To run real benchmark comparisons you have two options:

- set `OPENROUTER_API_KEY` and optionally `OPENROUTER_MODEL` to use the built-in OpenRouter runner
- set `BENCH_RUNNER_CMD` to a custom runner command if you want another provider or a true Claude Code harness

The runner contract is simple:

- GitHub sets `BENCH_TASK_FILE`, `BENCH_TASK_ID`, `BENCH_WORKDIR`, `BENCH_FIXTURE_DIR`, and `BENCH_OUTPUT_DIR`
- your runner command must execute the task and write `result.json` into `$BENCH_OUTPUT_DIR`
- `scripts/run-benchmark.sh` aggregates those task results into `summary.json`
- `scripts/compare-benchmarks.sh` decides `improved|regressed|no_significant_change`

See `docs/benchmarking.md` for setup, the OpenRouter path, and the expected `result.json` format.

## Logs

Hook logs are written under `~/.claude/logs/`. Session metadata and transcript paths are indexed in `~/.claude/logs/session-index.jsonl`.

## Docs

- `claudecfg/GUIDE.md` — full cheatsheet
- `claudecfg/agents/` — agent definitions
- `claudecfg/commands/` — command definitions
- `claudecfg/skills/` — skill definitions (commands that invoke agents)
- `docs/benchmarking.md` — benchmark runner contract and workflow usage

## Uninstall

To restore backup:
```bash
cp -r ~/.claude.backup.XXX/* ~/.claude/
```

Where `XXX` is the backup timestamp.

## License

MIT
