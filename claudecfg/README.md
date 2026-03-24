# Claude Code Configuration

## Directory Structure

### `claudecfg/`

Source configuration directory. Contains:

- `settings.json` — Claude Code main settings
- `agents/` — agent definitions (@manager, @explorer, @architect, @tester, @docwriter, @housekeeper)
- `commands/` — custom commands (/debug, /test, /design, /refactor, /review, /docs)
- `workflows/` — automation workflows
- `skills/` — skills
- `install.sh` — installation script
- `GUIDE.md` — complete guide

### `.claude/`

Target Claude Code directory (`$HOME/.claude/`). Files are copied here during installation. Contains user local configuration:

- `settings.local.json` — local settings (not tracked in git)

## Installation

```bash
cd claudecfg
./install.sh
```

The script:
1. Creates backup of current `~/.claude/` directory
2. Copies all files from `claudecfg/` to `~/.claude/`
3. Verifies installation

## Purpose

- `claudecfg/` — your configuration repository (store in git)
- `~/.claude/` — Claude Code working directory (don't store in git)
- `settings.local.json` — personal settings that should not be committed to repository