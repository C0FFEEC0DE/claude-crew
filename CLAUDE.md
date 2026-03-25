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

Commands `/debug`, `/test`, `/design`, `/refactor`, `/review` and the `/docs` skill invoke specialized agents.

## Agents

- `@m` — Manager (coordinates)
- `@e` — Explorer (codebase)
- `@a` — Architect (design)
- `@bug` — Bugbuster (find bugs)
- `@dbg` — Debugger (debug issues)
- `@t` — Tester (design, run, and verify tests)
- `@cr` — Code Reviewer (review)
- `@doc` — Docwriter (documentation)
- `@hk` — Housekeeper (cleanup)

## Docs

See `claudecfg/GUIDE.md` for full documentation.

## Repository Automation

Repository CI now includes:
- status badges in `README.md`
- `Validate`, `Hook Tests`, and `Security Scan` on every push and PR
- `Real Claude Code` on every push, plus manual runs with custom prompts, using headless Claude Code CLI via OpenRouter

OpenRouter-backed Claude Code is configured via repository secrets/variables. See `docs/real-claude-code.md`.
