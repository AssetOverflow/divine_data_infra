#!/usr/bin/env bash
set -Eeuo pipefail

# ================================
# DivineHaven - Development Setup (v2)
# ================================
# Uses consolidated 00_init.v2.sql with all schema features
# No need to run migrations for fresh start

# Resolve repo root (this script lives in scripts/shell_scripts/)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INIT_SQL="$ROOT/scripts/db_init/00_init.v2.sql"

echo "🚀 DivineHaven Development Setup (v2)"
echo "   Using: $INIT_SQL"
echo

echo "▶ Bringing up infrastructure (Postgres + Neo4j)…"
cd "$ROOT"
docker compose up -d db neo4j

# Wait for Postgres to be healthy
printf "⏳ Waiting for Postgres to be ready"
for i in {1..60}; do
  if docker compose exec db pg_isready -U postgres -d divinehaven >/dev/null 2>&1; then
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
  echo "🛠  Applying schema from $INIT_SQL (idempotent)…"
  docker compose exec -T db psql -U postgres -d divinehaven -v ON_ERROR_STOP=1 < "$INIT_SQL"
else
  echo "⚠️  $INIT_SQL not found. Exiting."
  exit 1
fi

echo
echo "ℹ️  Extensions present:"
docker compose exec db psql -U postgres -d divinehaven \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('timescaledb','vector','vectorscale','unaccent','pg_trgm') ORDER BY extname;"

echo
echo "ℹ️  Core tables:"
docker compose exec db psql -U postgres -d divinehaven \
  -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;" \
  | grep -E "verse|embedding|bucket|search_log|translation|book|chapter"

echo
echo "ℹ️  Vector indexes (should be diskann or hnsw):"
docker compose exec db psql -U postgres -d divinehaven \
  -c "SELECT indexname, indexdef FROM pg_indexes WHERE indexname LIKE '%embedding%ann%' OR indexname LIKE '%embedding%hnsw%' ORDER BY indexname;"

echo
echo "✅ Infrastructure up and schema applied (v2)."
echo
echo "📋 Next steps:"
echo "   1. Ingest Bible data:     ./scripts/shell_scripts/ingest_all.sh"
echo "   2. Generate embeddings:   uv run python manifest_cli.py embed-verses --dsn postgresql://postgres:Fr00pzPlz@localhost:5432/divinehaven"
echo "   3. Seed abs_index:        (see MIGRATION_STRATEGY.md step 4)"
echo "   4. Build chapter buckets: (see MIGRATION_STRATEGY.md step 5)"
echo "   5. Register run:          uv run python manifest_cli.py register-run manifest.json <dsn>"
echo "   6. Seed Neo4j:            docker compose exec backend uv run backend/etl/seed_graph.py"
