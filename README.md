# Claude Code Configuration

[![Validate](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/validate.yml)
[![Hook Tests](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/hooks-test.yml/badge.svg?branch=main)](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/hooks-test.yml)
[![Real Claude Code](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/real-claude-code.yml/badge.svg?branch=main)](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/real-claude-code.yml)
[![Security Scan](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/security-scan.yml/badge.svg?branch=main)](https://github.com/C0FFEEC0DE/claude-crew/actions/workflows/security-scan.yml)

Badges reflect the latest workflow result for the `main` branch.

## Quick Start

```bash
cd claudecfg
./install.sh
```

This will backup your current config and install the new one.

## Auto-Execution

In project folders (`~/projects/**`, `~/code/**`, `~/repos/**`, `~/work/**`), agents can execute safe commands automatically without confirmation.

### Safety
- Protected paths: `~/.ssh`, `~/.aws`, `/etc`, `/usr`, etc.
- Denied commands: `sudo`, `mkfs`, `dd`, `rm -rf /`
- Confirmation required outside project folders
- Release/deploy actions are intentionally out of scope for this profile

## What's Included

### Agents (9)

| Alias | Agent | Character | Purpose |
|-------|-------|-----------|---------|
| `@m` | Manager | Big Boss | Coordinates other agents |
| `@cr` | Code Reviewer | Toxic Senior | Code review + security |
| `@t` | Tester | Paranoid | Test design, execution, and verification |
| `@e` | Explorer | Nerd | Exploring code |
| `@a` | Architect | The Architect | System design + SOLID |
| `@bug` | Bugbuster | Cyber Detective | Bug hunting |
| `@dbg` | Debugger | Bug Hunter | Debugging issues |
| `@doc` | Docwriter | Wiki-Wiki | Documentation |
| `@hk` | Housekeeper | The Cleaner | Cleanup + DevOps |

Full names also work: `@manager`, `@code-reviewer`, etc.

### Slash Commands

Commands and skills that invoke specialized agents:

- `/debug` — debugging session
- `/test` — testing session (invokes @tester)
- `/design` — design session (invokes @architect)
- `/refactor` — refactoring session (invokes @housekeeper)
- `/review` — code review (invokes @code-reviewer)
- `/docs` — documentation skill session (invokes @docwriter)

### Workflows

- `workflows/bugfix.md` — fix a bug
- `workflows/new-feature.md` — implement feature
- `workflows/refactor.md` — refactor code
- `workflows/security-scan.md` — scan for private data (API keys, passwords, tokens)
- `workflows/release.md` — optional manual checklist, not part of the mandatory SDLC profile

### Hooks

The profile uses hooks as enforcement points, not markdown alone:

- `SessionStart` — bootstrap SDLC context and detect test/lint/build commands
- `UserPromptSubmit` — classify task into `bugfix|feature|refactor`
- `PreToolUse` / `PermissionRequest` — block destructive or out-of-scope actions, including force-push, `mkfs*`, and remote bootstrap pipes such as `curl|bash` or `wget|bash`
- `PostToolUse` / `PostToolUseFailure` — track edits plus successful or failed test/lint/build commands
- `TaskCompleted` / `Stop` / `TeammateIdle` — use the shared session state to block completion after missing verification or failed test/lint/build runs
- `SessionEnd` — index transcript paths and session metadata for later dataset work

`Stop` is enforced by the shell `stop-guard` hook only. This avoids prompt-hook failures on tool-only turns while still requiring a final assistant summary after code/config changes with verification status, review outcome, changed files, and remaining risks.

## Usage

### Call an agent directly (shortcuts)
```
@e explore the auth module
@cr review api.py
@t write tests for utils
@a design user auth
@bug find login bug
```

### Use full names
```
@explorer explore the auth module
@code-reviewer review api.py
@tester write tests for utils
```

### Use workflow (get plan)
```
@m fix bug in login
@manager implement new feature: user authentication
```

Manager can coordinate work, but completion is enforced by hooks. The expected flow is:
`discover -> design -> implement -> verify -> review -> docs when behavior changes -> cleanup`

### Use slash command
```
/debug
/test
/design
```

## Configuration

See `claudecfg/settings.json` for permissions and settings.

## CI and Claude Code

GitHub Actions now covers four layers:

- `Validate` — fast structural checks on every push and PR
- `Hook Tests` — behavior tests for the SDLC hook scripts
- `Real Claude Code` — headless Claude Code run via OpenRouter using the installed `claudecfg` profile
- `Security Scan` — repository secret and sensitive-file scan

All four workflows run automatically on every push.

### Fast CI

`Validate` runs:

- `bash scripts/validate.sh`
- shell syntax checks for `claudecfg/hooks/*.sh` and `scripts/*.sh`
- JSON checks for settings, hook cases, and benchmark metadata
- `git diff --check`

`Hook Tests` runs:

- `bash scripts/test-hooks.sh`

This harness verifies that key hooks block dangerous commands, classify prompts correctly, record verification state, reject incomplete stop summaries, and refuse completion after missing or failed verification when code changed.

### Real Claude Code

The repository now uses `.github/workflows/real-claude-code.yml` as the active coding-agent workflow.

That workflow:

- installs `claudecfg/*` into `~/.claude`
- installs the Claude Code CLI and runs `claude -p`
- routes Claude Code through OpenRouter
- runs automatically on every push
- can also be started manually with a custom prompt
- uploads `git status`, `git diff --stat`, the patch, and Claude output as workflow artifacts

Recommended model:

- `OPENROUTER_MODEL=z-ai/glm-4.7-flash`

## Logs

Hook logs are written under `~/.claude/logs/`. Session metadata and transcript paths are indexed in `~/.claude/logs/session-index.jsonl`.

## Docs

- `claudecfg/GUIDE.md` — full cheatsheet
- `claudecfg/agents/` — agent definitions
- `claudecfg/commands/` — command definitions
- `claudecfg/skills/` — skill definitions, including `/docs`
- `docs/real-claude-code.md` — real Claude Code workflow and OpenRouter setup

## Uninstall

To restore backup:
```bash
cp -r ~/.claude.backup.XXX/* ~/.claude/
```

Where `XXX` is the backup timestamp.

## License

MIT
