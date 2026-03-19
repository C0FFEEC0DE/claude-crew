# Claude Code Configuration

My personalized Claude Code setup with custom agents, commands, and workflows.

## Quick Start

```bash
cd claudecfg
./install.sh
```

This will backup your current config and install the new one.

## What's Included

### Agents (8)

| Alias | Agent | Character | Purpose |
|-------|-------|-----------|---------|
| `@m` | Manager | Big Boss | Coordinates other agents |
| `@cr` | Code Reviewer | Toxic Senior | Code review + security |
| `@t` | Tester | Paranoid | Writing tests (TDD, BDD) |
| `@e` | Explorer | Nerd | Exploring code |
| `@a` | Architect | The Architect | System design + SOLID |
| `@bug` | Bugbuster | Cyber Detective | Bug hunting |
| `@doc` | Docwriter | Wiki-Wiki | Documentation |
| `@hk` | Housekeeper | The Cleaner | Cleanup + DevOps |

Full names also work: `@manager`, `@code-reviewer`, etc.

### Slash Commands (10)

- `/debug` — debugging session
- `/test` — testing session
- `/design` — design session
- `/refactor` — refactoring session
- `/review` — code review
- `/train` — train model
- `/convert` — convert model
- `/deploy` — deploy
- `/gpu` — check GPU
- `/cleanup` — clean cache

### Workflows (4)

- `workflows/bugfix.md` — fix a bug
- `workflows/new-feature.md` — implement feature
- `workflows/refactor.md` — refactor code
- `workflows/release.md` — prepare release

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

### Execute full workflow automatically
```
@m fix bug in login, then execute the plan
@manager implement new feature: user authentication, then execute the plan
```
Claude will create a plan and automatically invoke all required agents.

### Use slash command
```
/debug
/test
/design
```

## Configuration

See `claudecfg/settings.json` for permissions and settings.

## Docs

- `claudecfg/GUIDE.md` — full cheatsheet
- `claudecfg/agents/` — agent definitions
- `claudecfg/commands/` — command definitions

## Uninstall

To restore backup:
```bash
cp -r ~/.claude.backup.XXX/* ~/.claude/
```

Where `XXX` is the backup timestamp.

## License

MIT