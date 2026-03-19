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

## Slash Commands

### General
- `/debug` — debugging session
- `/test` — testing session
- `/design` — design session
- `/refactor` — refactoring session
- `/review` — code review

### ML/AI
- `/train` — train model
- `/convert` — convert model (GGUF, Safetensors)
- `/deploy` — deploy to remote host
- `/gpu` — check GPU
- `/cleanup` — clean cache

## Subagents (shortcuts)

| Alias | Agent | Purpose |
|-------|-------|---------|
| `@m` | Manager | Coordinates other agents |
| `@cr` | Code Reviewer | Code review + security |
| `@t` | Tester | Writing tests (TDD, BDD) |
| `@e` | Explorer | Exploring code |
| `@a` | Architect | System design + SOLID |
| `@bug` | Bugbuster | Bug hunting |
| `@doc` | Docwriter | Documentation |
| `@hk` | Housekeeper | Cleanup + DevOps |

Also works: `@manager`, `@code-reviewer`, etc.

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

Predefined agent chains:

- `workflows/bugfix.md` — fix a bug
- `workflows/new-feature.md` — implement feature
- `workflows/refactor.md` — refactor code
- `workflows/release.md` — prepare release

### Usage

**Get plan only:**
```
@m fix bug in login
```
Manager returns a plan with steps and agents.

**Execute full workflow:**
```
@m fix bug in login, then execute the plan
```
Manager creates a plan, then Claude executes it by invoking agents automatically.

**Direct agent invocation:**
```
@explorer analyze auth module
@bugbuster find the bug
@architect design the fix
```

## Docs
- https://docs.anthropic.com/en/docs/claude-code/settings