# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Auto-execution configuration for project folders (`~/projects/**`, `~/code/**`, `~/repos/**`, `~/work/**`)
- Extended Bash permissions for common dev tools (rm, mkdir, cp, mv, cargo, go, etc.)
- `@debugger` agent for debugging sessions
- `/docs` skill command for documentation
- `skills/` folder for skill definitions
- GitHub Actions security-scan workflow
- CONTRIBUTING.md guidelines
- LICENSE file (MIT)
- Hook-based SDLC gate layer for session start, prompt classification, verification tracking, stop control, and transcript indexing
- Repository-level `Validate` and `Hook Tests` GitHub Actions workflows
- Behavior Benchmark workflow that runs the real Claude Code CLI inside isolated benchmark fixtures and uploads per-task artifacts
- OpenRouter-backed Claude Code benchmark setup documentation
- Behavioral benchmark documentation and summary gate script
- README status badges for repository workflows

### Changed
- Fixed agent types to use specialized types instead of `general-purpose`
- Reworked workflows around hook-gated execution instead of manager auto-execution promises
- Moved release/deploy out of the default profile into an optional manual checklist
- Updated docs to reflect implemented commands only
- Updated GUIDE.md with new agents and skills
- Updated GitHub Actions workflows to run on every push
- Replaced the custom benchmark coding-agent workflow with automatic real Claude Code CLI runs via OpenRouter
- Removed the standalone `Real Claude Code` smoke workflow so `Behavior Benchmark` is now the only real-agent GitHub workflow
- Tightened hook safety and completion gates: expanded dangerous-command blocking, unified failed test/lint/build gating, and moved `Stop` enforcement fully into shell hooks to avoid tool-only prompt-hook failures
- Moved `SubagentStop` enforcement into a shell hook so subagent stop validation no longer depends on prompt-hook message availability
- Updated shell stop gating so repos without detectable `test`/`lint`/`build` commands do not deadlock completion after config changes
- Added role-based subagent enforcement for `feature`, `bugfix`, `refactor`, `review`, and `docs` workflows before completion, with alias normalization and workflow-specific required roles
- Extended `SubagentStart` normalization to prefer alias, name, and subagent-type fields from snake_case and camelCase payloads before generic runtime types
- Updated workflow context and stop feedback with a stop-safe no-op footer for later replies in already dirty sessions
- Reworked benchmark automation so the main acceptance path now uses the real Claude Code CLI instead of a one-shot OpenRouter worker
- Improved GitHub Actions observability with readable Claude diagnostics in workflow logs, step summaries, and benchmark task artifacts
- Expanded `Behavior Benchmark` live logs with per-task metadata, prompt excerpts, raw Claude JSON excerpts, patch excerpts, and structured result dumps
- Added per-task `claude-debug.log` capture for the live benchmark path so empty-result failures can be debugged from Claude CLI traces
- Updated the live benchmark runner to use `--permission-mode acceptEdits` and surface `subtype`, `stop_reason`, and permission-denial diagnostics in task results
- Increased the default `Behavior Benchmark` turn budget from `8` to `32` per task
- Switched the default OpenRouter model for the live Claude Code benchmark path to `nvidia/nemotron-3-super-120b-a12b:free`

### Fixed
- New Feature workflow missing implementation and test steps
- Missing post-implementation code review in workflows
- `make lint` is now tracked as lint instead of build in hook session state
- `Stop`/`TaskCompleted`/`TeammateIdle` now consistently block after failed verification commands
- Added regression coverage for force-push, `mkfs*`, remote bootstrap pipes, tool-only stop turns, and incomplete final summaries
- Added shell-based regression coverage for incomplete subagent summaries and missing subagent assistant messages
- Fixed false `@general-purpose` role recording when specialized subagents were invoked through generic runtime payload fields
- Reduced stop-loop UX friction by surfacing a ready-to-use no-change footer in stop-guard feedback

## [1.0.0] - 2026-03-19

### Added
- Initial release with 8 agents
- 10 slash commands
- 5 workflows
- Manager agent with execution planning
- Security-scan workflow documentation
