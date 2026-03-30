# Claude Code — Cheatsheet

## Model
- Current default: `minimax-m2.5:cloud`

## Navigation
- `Read path/to/file` — read file
- `Grep "pattern"` — search in code
- `Glob "**/*.py"` — find files

## Search Discipline
- Prefer `Grep` or `rg` before opening files directly
- For large files, read targeted ranges instead of full-file rereads
- Reuse earlier reads from the session when possible

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

## Slash Commands

These commands invoke specialized agents:
The hooks enforce the actual handoff and stop gates; the commands below are the documented entry points.

### General
- `/manager` — manager-led orchestration session (invokes @manager)
- `/explore` — codebase exploration session (invokes @explorer)
- `/bug` — bug-hunting session (invokes @bugbuster)
- `/debug` — debugging session
- `/test` — testing session (invokes @tester)
- `/design` — design session (invokes @architect)
- `/refactor` — refactoring session (invokes @housekeeper, Veles)
- `/review` — code review (invokes @code-reviewer)
- `/docs` — documentation session (invokes @docwriter)

## Subagents (shortcuts)

| Alias | Agent | Purpose |
|-------|-------|---------|
| `@m` | Manager | Coordinates other agents |
| `@cr` | Code Reviewer | Code review + security |
| `@t` | Tester | Verification and regression testing |
| `@e` | Explorer | Exploring code |
| `@a` | Architect | System design + SOLID |
| `@bug` | Bugbuster | Bug hunting |
| `@dbg` | Debugger | Debugging issues |
| `@doc` | Docwriter | Documentation |
| `@hk` | Veles | Cleanup + bounded refactor hygiene |

Also works: `@manager`, `@code-reviewer`, etc.

### Slash command examples

```text
/manager fix flaky login tests end to end
/explore trace how auth state is loaded
/bug investigate why payments retry forever
/debug reproduce the cache invalidation issue
/test add regression coverage for password reset
/design design an API for report exports
/refactor clean up duplicated formatting helpers
/review review the authentication changes
/docs update the quickstart after CLI changes
```

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
- `UserPromptSubmit` — classify work as feature, bugfix, refactor, review, or docs and seed required subagent roles
- `PreToolUse` / `PermissionRequest` — block dangerous or out-of-scope commands, including force-push, `mkfs*`, and remote bootstrap pipes
- `PostToolUse` / `PostToolUseFailure` — record edits and successful or failed test/lint/build status
- `SubagentStart` / `SubagentStop` — enforce the subagent output contract with shell guards
- `TaskCompleted` / `TeammateIdle` / `Stop` — share the same gate logic and block completion after missing verification, failed test/lint/build runs, or missing required subagent roles
- `SessionEnd` — log transcript path and session metadata for later indexing

`Stop` is shell-enforced by `hooks/stop-guard.sh`, and `SubagentStop` is shell-enforced by `hooks/subagent-stop-guard.sh`. After code or config changes, the final assistant summary must include explicit summary lines for verification status, review outcome or pending review, changed files or `no files changed`, and remaining risks or `none`. If the repo exposes no detectable `test`, `lint`, or `build` command, the stop guard allows completion without deadlock, but the summary must explicitly say verification was not run and why. Feature, bugfix, refactor, review, and docs workflows also require role-specific specialist handoffs before completion, tracked in shared session state with alias normalization such as `@code-reviewer -> cr`. Manager-led orchestration itself is tracked separately through `manager_mode=orchestrate`, so top-level `@m` use is not treated as a required specialist handoff. For feature, bugfix, and refactor work, a recorded successful test command satisfies the tester side of that gate; otherwise `@t` is still required. `SubagentStart` normalization also accepts alias/name/subagent-type fields in both snake_case and camelCase before falling back to generic runtime types. `TeammateIdle` additionally blocks manager-led workflows that have not yet handed off to any specialist.

If a later reply in the same session makes no additional changes after earlier code or config edits, keep reporting the actual verification, review status, changed files, and remaining risks instead of switching to a no-change footer.

Required handoffs:
- `feature` -> successful verification or `@t`, plus `@cr` and one of `@e|@a`
- `bugfix` -> successful verification or `@t`, plus `@cr` and one of `@bug|@e|@dbg`
- `refactor` -> successful verification or `@t`, plus `@cr` and one of `@a|@e|@hk`
- `review` -> `@cr`
- `docs` -> `@doc`

Subagent summaries must include exact line prefixes for `Outcome:`, `Changed files:` or `No files changed:`, `Verification status:`, and `Remaining risks:` or `Next step:`.

## Standard Output

All subagents may include role-specific sections, but their handoff footer must use exact line prefixes that the shell guards recognize:

```text
Task: <name>
Status: <pending|in_progress|completed|blocked>
Outcome: <what was done or confirmed>
Changed files: <files or no changes>
Verification status: <passed|failed|not run|not required>
Remaining risks: <risks or none>
Next step: <next step>
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

**Manager-led execution:**
```
@m fix bug in login
```
Manager coordinates the workflow to completion or a concrete blocker.

**Plan only:**
```
@m plan only: fix bug in login
```
Manager returns the plan without continuing execution.

**Execution policy:**
- manager coordination is optional, but when invoked it should continue orchestration by default
- hooks, not markdown, enforce verification, required subagent roles, and stop conditions
- code review remains a required final gate for implementation work
- manager may parallelize multiple same-role specialists when their scopes are distinct; gates still care about roles, not instance count

**Direct agent invocation:**
```
@manager coordinate rollout for auth changes
@explorer analyze auth module
@bugbuster find the bug
@architect design the fix
@docwriter update the user-facing docs
```

## Docs
- https://docs.anthropic.com/en/docs/claude-code/settings
- https://code.claude.com/docs/en/hooks

## Repository Automation

Repository-level checks are separate from the local Claude profile:

- `.github/workflows/validate.yml` — structural validation on every push and PR
- `.github/workflows/hooks-test.yml` — deterministic hook behavior tests on every push and PR
- `.github/workflows/behavior-benchmark.yml` — behavioral acceptance tasks using the real Claude Code CLI inside benchmark fixtures
- `.github/workflows/security-scan.yml` — repository secret scan on every push and PR, plus weekly schedule

Benchmark support files:

- `tests/hooks/` — hook fixtures and assertions
- `bench/tasks/` — benchmark task definitions
- `bench/fixtures/` — benchmark fixture repositories
- `docs/benchmarking.md` — runner contract and GitHub setup
