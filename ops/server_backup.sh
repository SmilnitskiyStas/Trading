#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.server.yml}"
BACKUP_ROOT="${BACKUP_ROOT:-$PROJECT_DIR/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_ROOT/$STAMP"
ENV_FILE="$PROJECT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env not found in $PROJECT_DIR"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$ENV_FILE" "$BACKUP_DIR/.env.backup"

set -a
source "$ENV_FILE"
set +a

echo "Creating PostgreSQL dump..."
docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_DIR/postgres.sql"

echo "Copying ML model artifacts..."
docker cp trading-backend:/app/ml/models "$BACKUP_DIR/ml_models"
docker cp trading-backend:/app/ml/datasets "$BACKUP_DIR/ml_datasets"

echo "Saving Docker volume names..."
cat > "$BACKUP_DIR/backup_manifest.txt" <<EOF
created_at_utc=$STAMP
project_dir=$PROJECT_DIR
compose_file=$COMPOSE_FILE
postgres_container=trading-postgres
backend_container=trading-backend
postgres_dump=postgres.sql
ml_models_dir=ml_models
ml_datasets_dir=ml_datasets
EOF

ARCHIVE_PATH="$BACKUP_ROOT/trading_backup_$STAMP.tar.gz"
tar -czf "$ARCHIVE_PATH" -C "$BACKUP_ROOT" "$STAMP"

echo "Backup complete:"
echo "  folder: $BACKUP_DIR"
echo "  archive: $ARCHIVE_PATH"
