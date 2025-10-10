#!/usr/bin/env bash
set -Eeuo pipefail

# Resolve repo root (this script lives in scripts/)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INIT_SQL="$ROOT/scripts/db_init/00_init.sql"

echo "▶ Bringing up infrastructure (Postgres + Neo4j)…"
docker compose up -d db neo4j

# Wait for Postgres to be healthy
printf "⏳ Waiting for Postgres to be ready"
for i in {1..60}; do
  if docker exec divinehaven-db pg_isready -U postgres -d divinehaven >/dev/null 2>&1; then
    echo -e "\n✅ Postgres is ready."
    break
  fi
  printf "."; sleep 2
  if [ "$i" -eq 60 ]; then
    echo -e "\n❌ Timed out waiting for Postgres."
    exit 1
  fi
done

# Apply our consolidated init SQL (idempotent)
if [[ -f "$INIT_SQL" ]]; then
  echo "🛠  Applying schema & indexes from $INIT_SQL (idempotent)…"
  docker exec -i -w / divinehaven-db \
    psql -U postgres -d divinehaven -v ON_ERROR_STOP=1 -f /dev/stdin \
    < "$INIT_SQL"
else
  echo "⚠️  $INIT_SQL not found. Skipping schema apply."
fi

echo "ℹ️  Extensions present:"
docker exec -it divinehaven-db psql -U postgres -d divinehaven \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('timescaledb','vector','vectorscale');"

echo "ℹ️  Embedding table shape (expected vector(768)):"
docker exec -it divinehaven-db psql -U postgres -d divinehaven \
  -c "\d+ verse_embedding"

echo "ℹ️  Vector indexes:"
docker exec -it divinehaven-db psql -U postgres -d divinehaven \
  -c "\di *embedding*"

echo "✅ Infrastructure up and schema applied."
