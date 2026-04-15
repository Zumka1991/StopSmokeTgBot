---
name: deploy
description: Деплой StopSmokeTgBot на прод (root@5.253.59.251). Делает git pull + бэкап БД + docker compose up --build + healthcheck. Используй когда пользователь говорит "задеплой", "выкати", "обнови сервер", "deploy", "раскатай".
---

# Deploy StopSmokeTgBot

Цель: задеплоить текущий `master` репозитория `https://github.com/Zumka1991/StopSmokeTgBot` на прод-сервер.

## Сервер

- Хост: `root@5.253.59.251` (Ubuntu 24.04, Docker 28+)
- Путь к репе: `/apps/StopSmokeTgBot`
- Контейнер: `stopsmoke-bot`
- Скрипт деплоя на сервере: `/apps/StopSmokeTgBot/deploy.sh`
- SSH: ключ `~/.ssh/id_ed25519` (без пароля)

## Алгоритм

### 1. Префлайт (локально)

Перед деплоем убедись, что `master` отправлен в `origin`:

```bash
git status --short
git log origin/master..HEAD --oneline
```

- Если есть незакоммиченные правки — спроси юзера, что с ними делать (закоммитить? оставить? abort?).
- Если есть локальные коммиты ahead of origin/master — спроси, пушить ли их (`git push origin master`). Без push сервер задеплоит старую версию.

### 2. Запуск деплоя

Один SSH-вызов. `set -o pipefail` важен, чтобы не потерять exit code.

```bash
ssh root@5.253.59.251 'bash /apps/StopSmokeTgBot/deploy.sh' 2>&1
```

Скрипт сам:
- бэкапит `data/stopsmoke.db` через `sqlite3 .backup` в `data/backups/`,
- ротирует бэкапы старше 30 дней,
- делает `git pull --ff-only origin master`,
- `docker compose up -d --build`,
- ждёт до 15 сек что контейнер `running`,
- пишет всё в `/apps/StopSmokeTgBot/deploy.log`.

### 3. Постфлайт

После успешного деплоя:

```bash
ssh root@5.253.59.251 'docker logs --tail 30 stopsmoke-bot'
```

Покажи юзеру последние строки логов и подтверди что бот стартанул без exception'ов.

## Что делать при ошибке

- **`Your local changes ... would be overwritten`** на сервере — кто-то правил код прямо на проде. Спроси юзера, выкинуть ли изменения (`git reset --hard origin/master`) или сначала забрать их.
- **Healthcheck не прошёл** (контейнер не `running` за 15 сек) — тяни логи `docker logs stopsmoke-bot` и анализируй. Не пытайся «откатить» автоматически — спроси юзера.
- **SSH не отвечает** — проверь, что ключ на месте: `ls ~/.ssh/id_ed25519`. Если нет — см. «Bootstrap».

## Bootstrap (одноразово, если ключа нет)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@5.253.59.251
```

## Ограничения

- Никогда не запускай `git reset --hard` на сервере без явного "да" от юзера.
- Никогда не удаляй бэкапы вручную — это делает скрипт.
- Если юзер просит откатить версию — спроси, на какой SHA, и сделай `git reset --hard <sha> && docker compose up -d --build` явно.
