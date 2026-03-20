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

### Changed
- Fixed agent types to use specialized types instead of `general-purpose`
- Updated workflows to include mandatory code review
- Fixed bugfix workflow to include documentation step
- Fixed release workflow order (docs before review)
- Updated GUIDE.md with new agents and skills

### Fixed
- New Feature workflow missing implementation and test steps
- Missing post-implementation code review in workflows

## [1.0.0] - 2026-03-19

### Added
- Initial release with 8 agents
- 10 slash commands
- 5 workflows
- Manager agent with execution planning
- Security-scan workflow documentation
