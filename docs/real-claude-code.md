# Real Claude Code

This repository uses the real Claude Code CLI in headless mode routed through OpenRouter.

The active coding-agent workflow is:

- `.github/workflows/real-claude-code.yml`

## What It Does

On every push, the workflow:

1. checks out the repository
2. installs `claudecfg/*` into `~/.claude`
3. installs the Claude Code CLI
4. runs `claude -p`
5. routes Claude Code through OpenRouter
6. fails if Claude output JSON is missing, invalid, or has an empty `.result`
7. uploads `git status`, `git diff --stat`, the patch, and Claude output as artifacts

You can also run it manually with a custom prompt using `workflow_dispatch`.

## Required GitHub Setup

Repository settings:

1. `Settings -> Secrets and variables -> Actions -> New repository secret`
2. Add `OPENROUTER_API_KEY`
3. `Settings -> Secrets and variables -> Actions -> Variables`
4. Add `OPENROUTER_MODEL`

Recommended value:

```text
z-ai/glm-4.7-flash
```

## Why OpenRouter

OpenRouter is used here as an Anthropic-compatible backend for Claude Code.

The workflow sets:

```text
ANTHROPIC_BASE_URL=https://openrouter.ai/api
```

and exports:

```text
ANTHROPIC_AUTH_TOKEN=${OPENROUTER_API_KEY}
ANTHROPIC_API_KEY=
```

to the action.

## Trigger Behavior

- `push` — runs automatically and generates a default prompt from the pushed commit range
- `workflow_dispatch` — lets you provide your own prompt and optional model override

## Notes

- This is the real Claude Code runtime, not a custom benchmark worker.
- The repository profile under `claudecfg/` is installed into `~/.claude` before Claude runs.
- The workflow is configured with `contents: read`, so any suggested file changes stay in the runner workspace and are captured as artifacts.
- A green run means more than process survival: the Claude CLI must also emit valid JSON with a non-empty `.result`.
- This workflow is still a smoke test for the real runtime path. Behavioral acceptance is enforced separately by `.github/workflows/behavior-benchmark.yml`.
- The GitHub Action wrapper was removed from the automatic path because it currently fails on `push` with `Unsupported event type: push`, so the workflow now calls the Claude Code CLI directly.
