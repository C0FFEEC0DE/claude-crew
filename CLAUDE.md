# Project Context

This directory contains Claude Code configuration.

## Auto-Execution

In project folders (`~/projects/**`, `~/code/**`, etc.), agents execute commands automatically without confirmation.

## Quick Start

```bash
cd claudecfg
./install.sh
```

## Agents

Use `@manager` to coordinate other agents:

- `@explorer` — explore code
- `@architect` — design solutions
- `@bugbuster` — find bugs
- `@tester` — write tests
- `@code-reviewer` — code review
- `@docwriter` — write docs
- `@housekeeper` — cleanup

## Commands

- `/debug`, `/test`, `/design`, `/refactor`, `/review`, `/docs`
- `/train`, `/convert`, `/deploy`, `/gpu`, `/cleanup`

Commands `/debug`, `/test`, `/design`, `/refactor`, `/review`, `/docs` invoke specialized agents.

## Agents

- `@m` — Manager (coordinates)
- `@e` — Explorer (codebase)
- `@a` — Architect (design)
- `@bug` — Bugbuster (find bugs)
- `@dbg` — Debugger (debug issues)
- `@t` — Tester (write tests)
- `@cr` — Code Reviewer (review)
- `@doc` — Docwriter (documentation)
- `@hk` — Housekeeper (cleanup)

## Docs

See `claudecfg/GUIDE.md` for full documentation.