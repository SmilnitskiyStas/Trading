#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.server.yml}"
RESTORE_SOURCE="${1:-}"
ENV_FILE="$PROJECT_DIR/.env"

if [[ -z "$RESTORE_SOURCE" ]]; then
  echo "Usage: bash ops/server_restore.sh /path/to/backup_dir_or_archive"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env not found in $PROJECT_DIR"
  exit 1
fi

WORK_DIR=""
if [[ -f "$RESTORE_SOURCE" ]]; then
  WORK_DIR="$(mktemp -d)"
  tar -xzf "$RESTORE_SOURCE" -C "$WORK_DIR"
  RESTORE_DIR="$(find "$WORK_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
else
  RESTORE_DIR="$RESTORE_SOURCE"
fi

if [[ ! -f "$RESTORE_DIR/postgres.sql" ]]; then
  echo "postgres.sql not found in $RESTORE_DIR"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

echo "Restoring PostgreSQL dump..."
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$RESTORE_DIR/postgres.sql"

if [[ -d "$RESTORE_DIR/ml_models" ]]; then
  echo "Restoring ML model artifacts..."
  docker cp "$RESTORE_DIR/ml_models/." trading-backend:/app/ml/models/
fi

if [[ -d "$RESTORE_DIR/ml_datasets" ]]; then
  echo "Restoring ML dataset artifacts..."
  docker cp "$RESTORE_DIR/ml_datasets/." trading-backend:/app/ml/datasets/
fi

echo "Restore complete from $RESTORE_DIR"
