# Real Claude Code

This repository uses the official Claude Code GitHub Action routed through OpenRouter.

The active coding-agent workflow is:

- `.github/workflows/real-claude-code.yml`

## What It Does

On every push, the workflow:

1. checks out the repository
2. installs `claudecfg/*` into `~/.claude`
3. runs `anthropics/claude-code-action@v1`
4. routes the action through OpenRouter
5. uploads `git status`, `git diff --stat`, and the patch as artifacts

You can also run it manually with a custom prompt using `workflow_dispatch`.

## Required GitHub Setup

Repository settings:

1. `Settings -> Secrets and variables -> Actions -> New repository secret`
2. Add `OPENROUTER_API_KEY`
3. `Settings -> Secrets and variables -> Actions -> Variables`
4. Add `OPENROUTER_MODEL`

Recommended value:

```text
anthropic/claude-haiku-4.5
```

## Why OpenRouter

OpenRouter is used here as an Anthropic-compatible backend for the official Claude Code action.

The workflow sets:

```text
ANTHROPIC_BASE_URL=https://openrouter.ai/api
```

and passes:

```text
anthropic_api_key: ${{ secrets.OPENROUTER_API_KEY }}
```

to the action.

## Trigger Behavior

- `push` — runs automatically and generates a default prompt from the pushed commit range
- `workflow_dispatch` — lets you provide your own prompt and optional model override

## Notes

- This is the real Claude Code runtime, not a custom benchmark worker.
- The repository profile under `claudecfg/` is installed into `~/.claude` before Claude runs.
- The workflow is configured with `contents: read`, so any suggested file changes stay in the runner workspace and are captured as artifacts.
