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
- Real Claude Code workflow via OpenRouter using headless Claude Code CLI with installed repo config
- OpenRouter-backed Claude Code setup documentation
- README status badges for repository workflows

### Changed
- Fixed agent types to use specialized types instead of `general-purpose`
- Reworked workflows around hook-gated execution instead of manager auto-execution promises
- Moved release/deploy out of the default profile into an optional manual checklist
- Updated docs to reflect implemented commands only
- Updated GUIDE.md with new agents and skills
- Updated GitHub Actions workflows to run on every push
- Replaced the custom benchmark coding-agent workflow with automatic real Claude Code CLI runs via OpenRouter
- Tightened hook safety and completion gates: expanded dangerous-command blocking, unified failed test/lint/build gating, and moved `Stop` enforcement fully into shell hooks to avoid tool-only prompt-hook failures

### Fixed
- New Feature workflow missing implementation and test steps
- Missing post-implementation code review in workflows
- `make lint` is now tracked as lint instead of build in hook session state
- `Stop`/`TaskCompleted`/`TeammateIdle` now consistently block after failed verification commands
- Added regression coverage for force-push, `mkfs*`, remote bootstrap pipes, tool-only stop turns, and incomplete final summaries

## [1.0.0] - 2026-03-19

### Added
- Initial release with 8 agents
- 10 slash commands
- 5 workflows
- Manager agent with execution planning
- Security-scan workflow documentation
