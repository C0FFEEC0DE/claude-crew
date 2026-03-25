# Project Context

This directory contains Claude Code configuration.

## Profile

This profile is hook-gated:
- discover -> design -> implement -> verify -> review -> docs when behavior changes -> cleanup
- release/deploy automation is intentionally disabled
- session metadata is logged for later audit or dataset indexing

## Quick Start

```bash
cd claudecfg
./install.sh
```

## Commands

- `/debug`, `/test`, `/design`, `/refactor`, `/review`, `/docs`

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
