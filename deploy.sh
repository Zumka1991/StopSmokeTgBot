#!/usr/bin/env bash
# Деплой StopSmokeTgBot. Запускается на сервере (или удалённо через SSH).
# Делает: бэкап БД -> git pull -> build -> up -> healthcheck. Логирует в deploy.log.
set -Eeuo pipefail

REPO_DIR="/apps/StopSmokeTgBot"
SERVICE="bot"
CONTAINER="stopsmoke-bot"
BACKUP_DIR="$REPO_DIR/data/backups"
LOG_FILE="$REPO_DIR/deploy.log"
HEALTH_TIMEOUT=15

cd "$REPO_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }
fail() { log "FAIL: $*"; exit 1; }
trap 'fail "aborted at line $LINENO"' ERR

# Выбираем compose: предпочитаем v2 (docker compose), fallback на legacy.
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  fail "docker compose не найден"
fi

log "=== deploy start ($DC) ==="

# 1. Бэкап SQLite-базы (если есть).
mkdir -p "$BACKUP_DIR"
DB_FILE="$REPO_DIR/data/stopsmoke.db"
if [[ -f "$DB_FILE" ]]; then
  BACKUP_FILE="$BACKUP_DIR/stopsmoke-$(date +%Y%m%d-%H%M%S).db"
  # .backup безопаснее cp (учитывает WAL и блокировки).
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"
  else
    cp "$DB_FILE" "$BACKUP_FILE"
  fi
  log "backup: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
  # Чистим бэкапы старше 30 дней.
  find "$BACKUP_DIR" -name 'stopsmoke-*.db' -mtime +30 -delete
else
  log "backup: $DB_FILE не найден, пропуск"
fi

# 2. Git pull. fast-forward only — если есть локальные правки на сервере, упадём.
OLD_SHA=$(git rev-parse --short HEAD)
git fetch --quiet origin
NEW_SHA=$(git rev-parse --short origin/master)
if [[ "$OLD_SHA" == "$NEW_SHA" ]]; then
  log "no changes (HEAD=$OLD_SHA). Принудительный rebuild+restart всё равно."
fi
git pull --ff-only origin master
log "git: $OLD_SHA -> $NEW_SHA"

# 3. Build + up. --build пересоберёт образ если изменился Dockerfile/код.
$DC up -d --build
log "compose up done"

# 4. Healthcheck — ждём что контейнер running.
for i in $(seq 1 "$HEALTH_TIMEOUT"); do
  STATUS=$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "missing")
  if [[ "$STATUS" == "running" ]]; then
    log "health: $CONTAINER running (после ${i}s)"
    log "=== deploy ok ==="
    exit 0
  fi
  sleep 1
done
fail "контейнер $CONTAINER не запустился за ${HEALTH_TIMEOUT}s (status=$STATUS). Логи: docker logs $CONTAINER"
