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

| Agent | Character | Purpose |
|-------|-----------|---------|
| `@manager` | Big Boss | Coordinates other agents |
| `@code-reviewer` | Toxic Senior | Code review + security |
| `@tester` | Paranoid | Writing tests (TDD, BDD) |
| `@explorer` | Nerd | Exploring code |
| `@architect` | The Architect | System design + SOLID |
| `@bugbuster` | Cyber Detective | Bug hunting |
| `@docwriter` | Wiki-Wiki | Documentation |
| `@housekeeper` | The Cleaner | Cleanup + DevOps |

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

### Call an agent directly
```
@explorer explore the auth module
@code-reviewer review api.py
@tester write tests for utils
```

### Use workflow
```
@manager fix bug in login
@manager implement new feature: user authentication
```

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