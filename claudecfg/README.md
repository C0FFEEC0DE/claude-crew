# Claude Code Configuration

## Структура директорий

### `claudecfg/`

Исходная директория с конфигурацией. Содержит:

- `settings.json` — основные настройки Claude Code
- `agents/` — определения агентов (@manager, @explorer, @architect, @tester, @docwriter, @housekeeper)
- `commands/` — пользовательские команды (/debug, /test, /design, /refactor, /review, /docs)
- `workflows/` —workflows для автоматизации
- `skills/` — навыки (skills)
- `install.sh` — скрипт установки
- `GUIDE.md` — полное руководство

### `.claude/`

Целевая директория Claude Code ( `$HOME/.claude/` ). Сюда копируются файлы при установке. Здесь хранится локальная конфигурация пользователя:

- `settings.local.json` — локальные настройки (не отслеживается в git)

## Установка

```bash
cd claudecfg
./install.sh
```

Скрипт:
1. Создает backup текущей директории `~/.claude/`
2. Копирует все файлы из `claudecfg/` в `~/.claude/`
3. Проверяет установку

## Смысл

- `claudecfg/` — это репозиторий с вашей конфигурацией (храните в git)
- `~/.claude/` — рабочая директория Claude Code (не храните в git)
- `settings.local.json` — персональные настройки, которые не должны попадать в репозиторий