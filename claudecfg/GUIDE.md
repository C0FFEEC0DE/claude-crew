# Claude Code — Cheatsheet

## Model
- `/model` — change model
- Current: `minimax-m2.5:cloud`

## Navigation
- `Read path/to/file` — read file
- `Grep "pattern"` — search in code
- `Glob "**/*.py"` — find files

## Planning
- `EnterPlanMode` — for tasks >2-3 files
- `TaskCreate` — create task
- `TaskList` — list tasks

## Git
- **Never** `git reset --hard`, `git push --force` without asking
- Always show `git status` + `git diff` before commit

## Important
- Don't delete files without asking
- Don't change configs automatically
- Don't commit myself
- Don't touch .env, secrets, credentials
- No release/deploy automation in this profile

## Slash Commands (Skills)

These commands invoke specialized agents:

### General
- `/debug` — debugging session
- `/test` — testing session (invokes @tester)
- `/design` — design session (invokes @architect)
- `/refactor` — refactoring session (invokes @housekeeper)
- `/review` — code review (invokes @code-reviewer)
- `/docs` — documentation session (invokes @docwriter)

## Subagents (shortcuts)

| Alias | Agent | Purpose |
|-------|-------|---------|
| `@m` | Manager | Coordinates other agents |
| `@cr` | Code Reviewer | Code review + security |
| `@t` | Tester | Writing tests (TDD, BDD) |
| `@e` | Explorer | Exploring code |
| `@a` | Architect | System design + SOLID |
| `@bug` | Bugbuster | Bug hunting |
| `@dbg` | Debugger | Debugging issues |
| `@doc` | Docwriter | Documentation |
| `@hk` | Housekeeper | Cleanup + DevOps |

Also works: `@manager`, `@code-reviewer`, etc.

## Auto-Execution

When working in a project folder (`~/projects/**`, `~/code/**`, `~/repos/**`, `~/work/**`):
- Commands execute automatically
- No confirmation needed for safe operations
- Security restrictions still apply (no sudo, rm -rf /, etc.)
- Hooks still enforce SDLC gates and block release/deploy actions

Outside project folders, confirmation is required.

## Hook-Gated SDLC

Mandatory flow:

`discover -> design -> implement -> verify -> review -> docs when behavior changes -> cleanup`

Main checkpoints:

- `SessionStart` — bootstrap SDLC context and detect test/lint/build commands
- `UserPromptSubmit` — classify work as feature, bugfix, or refactor
- `PreToolUse` / `PermissionRequest` — block dangerous or out-of-scope commands, including force-push, `mkfs*`, and remote bootstrap pipes
- `PostToolUse` / `PostToolUseFailure` — record edits and successful or failed test/lint/build status
- `SubagentStart` / `SubagentStop` — enforce the subagent output contract with shell guards
- `TaskCompleted` / `TeammateIdle` / `Stop` — share the same gate logic and block completion after missing verification or failed test/lint/build runs
- `SessionEnd` — log transcript path and session metadata for later indexing

`Stop` is shell-enforced by `hooks/stop-guard.sh`, and `SubagentStop` is shell-enforced by `hooks/subagent-stop-guard.sh`. After code or config changes, the final assistant summary must mention verification status, review outcome or pending review, changed files or `no files changed`, and remaining risks or `none`. If the repo exposes no detectable `test`, `lint`, or `build` command, the stop guard allows completion without deadlock, but the summary must explicitly say verification was not run and why. Subagent summaries must include outcome, changed files or `no files changed`, verification status, and remaining risks or next step.

## Standard Output

All subagents use the same format:

```
╔══════════════════════════════════════════════════════╗
║  TASK: <name>                                        ║
║  STATUS: <pending|in_progress|completed|blocked>     ║
╠══════════════════════════════════════════════════════╣
║  RESULTS:                                             ║
║  - <result 1>                                        ║
║  - <result 2>                                        ║
╠══════════════════════════════════════════════════════╣
║  NEXT:                                                ║
║  - <next step>                                       ║
╚══════════════════════════════════════════════════════╝
```

## CLAUDE.md
Create `./CLAUDE.md` in project — put project context there (max 50 lines).

## Workflows

Predefined workflows:

- `workflows/bugfix.md` — fix a bug
- `workflows/new-feature.md` — implement feature
- `workflows/refactor.md` — refactor code
- `workflows/security-scan.md` — scan for private data (API keys, passwords, tokens)
- `workflows/release.md` — optional manual checklist, not part of the required SDLC path

### Usage

**Get plan only:**
```
@m fix bug in login
```
Manager returns a plan with steps and agents.

**Execution policy:**
- manager coordination is optional
- hooks, not markdown, enforce verification and stop conditions
- code review remains a required final gate for implementation work

**Direct agent invocation:**
```
@explorer analyze auth module
@bugbuster find the bug
@architect design the fix
```

## Docs
- https://docs.anthropic.com/en/docs/claude-code/settings
- https://code.claude.com/docs/en/hooks

## Repository Automation

Repository-level checks are separate from the local Claude profile:

- `.github/workflows/validate.yml` — structural validation on every push and PR
- `.github/workflows/hooks-test.yml` — deterministic hook behavior tests on every push and PR
- `.github/workflows/security-scan.yml` — repository secret scan on every push and PR, plus weekly schedule
- `.github/workflows/benchmark.yml` — benchmark comparison on every push, mock on PRs, and manual/scheduled runs for full comparisons

Benchmark support files:

- `tests/hooks/` — hook fixtures and assertions
- `bench/tasks/` — benchmark task definitions
- `bench/fixtures/` — benchmark fixture repositories
- `docs/benchmarking.md` — runner contract and GitHub setup
