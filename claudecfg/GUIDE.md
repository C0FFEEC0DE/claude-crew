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

## Subagents

- `@manager` — coordinates other agents
- `@code-reviewer` — code review
- `@tester` — writes tests
- `@explorer` — explores code
- `@architect` — designs solutions
- `@bugbuster` — finds bugs
- `@docwriter` — writes docs
- `@housekeeper` — routine, cleanup, rituals

## Standard Output

All subagents use the same format:

```
╔══════════════════════════════════════════════════════╗
║  TASK: <name>                                        ║
║  STATUS: <pending|in_progress|completed|blocked>     ║
╠══════════════════════════════════════════════════════╣
║  RESULTS:                                            ║
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

Usage: "@manager fix bug in login" or use directly.

## Docs
- https://docs.anthropic.com/en/docs/claude-code/settings