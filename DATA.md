Data Reproducibility and Restore Guide

This repository avoids committing large data. Use one of two paths:

- Restore from backups (preferred if you have tarballs)
- Rebuild from sources (schema, JSON assets, and scripts)

Prerequisites
- Docker + Docker Compose
- Export bundle path: `backend_data_bundle/export` (or repo root with compose)

1) Restore From Backups
- Create or reuse volumes, then untar archives into them.
- Volumes used by compose:
  - TimescaleDB: divinehaven_db_data (or your project-scoped name)
  - Neo4j data/logs: divinehaven_neo4j_data, divinehaven_neo4j_logs
  - Redis: divinehaven_redis_data

Commands
- Create volumes (adjust names to your environment):
  docker volume create divinehaven_db_data
  docker volume create divinehaven_neo4j_data
  docker volume create divinehaven_neo4j_logs
  docker volume create divinehaven_redis_data

- Extract backups (replace filenames):
  docker run --rm -v divinehaven_db_data:/volume -v $(pwd):/backup alpine:3.20 sh -c "cd /volume && tar -xzf /backup/timescaledb-YYYYMMDDTHHMMSS.tar.gz"
  docker run --rm -v divinehaven_neo4j_data:/volume -v $(pwd):/backup alpine:3.20 sh -c "cd /volume && tar -xzf /backup/neo4j_data-YYYYMMDDTHHMMSS.tar.gz"
  docker run --rm -v divinehaven_neo4j_logs:/volume -v $(pwd):/backup alpine:3.20 sh -c "cd /volume && tar -xzf /backup/neo4j_logs-YYYYMMDDTHHMMSS.tar.gz"
  docker run --rm -v divinehaven_redis_data:/volume -v $(pwd):/backup alpine:3.20 sh -c "cd /volume && tar -xzf /backup/redis-YYYYMMDDTHHMMSS.tar.gz"

- Bring up services:
  docker compose up -d db neo4j redis backend

2) Rebuild From Sources (cold start)
- Do NOT auto-ingest on boot. Schema initializes only.
- Steps:
  1. Start services:
     docker compose up -d db neo4j redis backend
  2. Ingest canonical Bible JSONs into TimescaleDB:
     uv run python manifest_cli.py ingest --source unified_json_bibles
  3. (Optional) Generate embeddings if missing:
     uv run python manifest_cli.py embed --model embeddinggemma --dim 768 --batch-size 64
  4. Build Neo4j graph from DB (idempotent):
     uv run python manifest_cli.py graphify --from-db
  5. Apply post-ingest indexes:
     bash scripts/shell_scripts/apply_indexes.sh

3) Backups
- Create archives into `backend_data_bundle/backups`:
  ./scripts/backup_data_volumes.sh backend_data_bundle/backups

4) Safety
- Never run ingest if you’ve restored volumes. Ingestion is deliberate.
- Embeddings are compute-heavy; run only if required.

