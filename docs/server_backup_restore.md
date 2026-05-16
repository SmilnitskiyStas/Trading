# Server Backup and Restore

This runbook covers two critical assets:

- PostgreSQL runtime data
- ML artifacts stored under `/app/ml/models` and `/app/ml/datasets`

## Create a backup on the server

Run from the project root on the server:

```bash
bash ops/server_backup.sh
```

What it creates:

- PostgreSQL dump: `postgres.sql`
- copied ML model artifacts
- copied ML dataset artifacts
- backup manifest
- compressed archive under `backups/`

## Restore from a backup

Run from the project root on the server:

```bash
bash ops/server_restore.sh /full/path/to/backup_dir
```

or from an archive:

```bash
bash ops/server_restore.sh /full/path/to/trading_backup_20260516T120000Z.tar.gz
```

## Notes

- Restore expects the server stack to be running.
- The scripts use `docker compose -f docker-compose.server.yml`.
- Keep backup archives outside the container lifecycle.
- If you restore ML artifacts, validate the active runtime model again through:

```bash
python backend/scripts/manage_remote_model_pin.py \
  --base-url http://SERVER_IP:8000 \
  --action active \
  --symbol BTC/USDT \
  --timeframe 1h
```
