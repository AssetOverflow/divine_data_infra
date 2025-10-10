#!/usr/bin/env bash
set -Eeuo pipefail

# ================================
# DivineHaven - Complete Data Pipeline
# ================================
# Runs the entire process from scratch:
#   1. Initialize database schema
#   2. Ingest Bible data from JSON files
#   3. Generate embeddings with Ollama
#   4. Populate derived columns (abs_index, buckets)
#   5. Register run manifest
#   6. Seed Neo4j graph database
#
# Prerequisites:
#   - Docker Compose (for db, neo4j containers)
#   - uv (Python package manager)
#   - Ollama running with embeddinggemma model
#   - Bible JSON files in unified_json_bibles/

# Configuration
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BIBLES_DIR="${BIBLES_DIR:-$ROOT/unified_json_bibles}"
DSN="${DSN:-postgresql://postgres:Fr00pzPlz@localhost:5432/divinehaven}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-embeddinggemma}"
EMBEDDING_DIM="${EMBEDDING_DIM:-768}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_step() {
  echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $1"
}

log_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
  echo -e "${RED}❌ $1${NC}"
}

log_warn() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

# Preflight checks
log_step "Running preflight checks..."

if ! command -v docker &> /dev/null; then
  log_error "Docker not found. Install Docker first."
  exit 1
fi

if ! command -v uv &> /dev/null; then
  log_error "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

if [[ ! -d "$BIBLES_DIR" ]]; then
  log_error "BIBLES_DIR not found: $BIBLES_DIR"
  echo "   Set BIBLES_DIR environment variable or place files in $ROOT/unified_json_bibles/"
  exit 1
fi

if ! curl -sf "$OLLAMA_HOST/api/tags" &> /dev/null; then
  log_warn "Ollama not reachable at $OLLAMA_HOST"
  echo "   Start Ollama and pull the model: ollama pull $EMBEDDING_MODEL"
  read -p "   Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

log_success "Preflight checks passed"
echo

# ================================
# Step 1: Initialize Infrastructure
# ================================
log_step "Step 1/6: Initializing database infrastructure..."
cd "$ROOT"

if [[ ! -f "scripts/shell_scripts/dev_up_v2.sh" ]]; then
  log_error "dev_up_v2.sh not found. Run this script from project root."
  exit 1
fi

bash scripts/shell_scripts/dev_up_v2.sh

log_success "Database schema initialized"
echo

# ================================
# Step 2: Ingest Bible Data
# ================================
log_step "Step 2/6: Ingesting Bible data from $BIBLES_DIR..."

if [[ ! -f "scripts/shell_scripts/ingest_all.sh" ]]; then
  log_error "ingest_all.sh not found"
  exit 1
fi

bash scripts/shell_scripts/ingest_all.sh

log_success "Bible data ingested"
echo

# Verify verse count
VERSE_COUNT=$(docker compose exec -T -e PGPASSWORD=Fr00pzPlz db \
  psql -U postgres -d divinehaven -tAc "SELECT COUNT(*) FROM verse;")
log_step "Verses in database: $VERSE_COUNT"

if [[ "$VERSE_COUNT" -eq 0 ]]; then
  log_error "No verses found after ingestion. Check logs above."
  exit 1
fi

# ================================
# Step 3: Generate Embeddings
# ================================
log_step "Step 3/6: Generating embeddings with $EMBEDDING_MODEL..."

uv run python manifest_cli.py embed-verses \
  --dsn "$DSN" \
  --model "$EMBEDDING_MODEL" \
  --dim "$EMBEDDING_DIM" \
  --api-base "$OLLAMA_HOST" \
  --batch 256 \
  --workers 8 \
  --fetch-page 10000

log_success "Embeddings generated"
echo

# ================================
# Step 4: Populate Derived Columns
# ================================
log_step "Step 4/6: Populating derived columns (abs_index, buckets)..."

# 4a: Seed verse_abs_index
log_step "  → Seeding verse_abs_index..."
docker compose exec -T -e PGPASSWORD=Fr00pzPlz db psql -U postgres -d divinehaven -v ON_ERROR_STOP=1 <<'SQL'
WITH ordered AS (
  SELECT verse_id,
         translation_code,
         row_number() OVER (
           PARTITION BY translation_code
           ORDER BY book_number, chapter_number, verse_number, suffix
         )::bigint AS rn
  FROM verse
  WHERE verse_abs_index IS NULL
)
UPDATE verse v
SET verse_abs_index = o.rn
FROM ordered o
WHERE v.verse_id = o.verse_id;
SQL

log_success "  verse_abs_index populated"

# 4b: Build chapter buckets
log_step "  → Building chapter buckets..."
docker compose exec -T -e PGPASSWORD=Fr00pzPlz db psql -U postgres -d divinehaven -v ON_ERROR_STOP=1 <<'SQL'
-- Insert chapter buckets
WITH chapters AS (
  SELECT DISTINCT translation_code, book_number, chapter_number
  FROM verse
)
INSERT INTO verse_bucket (translation_code, level, book_number, chapter_number, label)
SELECT c.translation_code, 'chapter'::bucket_level, c.book_number, c.chapter_number,
       format('%s %s', c.book_number, c.chapter_number)
FROM chapters c
ON CONFLICT (translation_code, level, book_number, chapter_number) DO NOTHING;

-- Link verses to chapter buckets
WITH j AS (
  SELECT vb.bucket_id, v.verse_id,
         row_number() OVER (
           PARTITION BY vb.bucket_id
           ORDER BY v.book_number, v.chapter_number, v.verse_number, v.suffix
         )::int AS ord
  FROM verse v
  JOIN verse_bucket vb
    ON vb.translation_code = v.translation_code
   AND vb.level = 'chapter'
   AND vb.book_number = v.book_number
   AND vb.chapter_number = v.chapter_number
)
INSERT INTO verse_bucket_member (bucket_id, verse_id, ord)
SELECT j.bucket_id, j.verse_id, j.ord
FROM j
ON CONFLICT (bucket_id, verse_id) DO NOTHING;
SQL

log_success "  Chapter buckets built"
echo

# ================================
# Step 5: Register Run Manifest
# ================================
log_step "Step 5/6: Registering run manifest..."

if [[ -f "manifest.json" ]]; then
  uv run python manifest_cli.py register-run \
    manifest.json \
    "$DSN"
  log_success "Run manifest registered"
else
  log_warn "manifest.json not found. Skipping registration."
  log_warn "   Create one with: uv run python manifest_cli.py init"
fi
echo

# ================================
# Step 6: Seed Neo4j Graph
# ================================
log_step "Step 6/6: Seeding Neo4j graph database..."

# Wait for Neo4j to be ready
printf "⏳ Waiting for Neo4j to be ready"
for i in {1..30}; do
  if docker compose exec neo4j cypher-shell -u neo4j -p Fr00pzPlz "RETURN 1" &> /dev/null; then
    echo -e "\n✅ Neo4j is ready."
    break
  fi
  printf "."; sleep 2
  if [ "$i" -eq 30 ]; then
    echo -e "\n⚠️  Neo4j not ready. Skipping graph seeding."
    break
  fi
done

if docker compose exec neo4j cypher-shell -u neo4j -p Fr00pzPlz "RETURN 1" &> /dev/null; then
  docker compose exec backend uv run backend/etl/seed_graph.py
  log_success "Neo4j graph seeded"
else
  log_warn "Neo4j not accessible. Run manually later: docker compose exec backend uv run backend/etl/seed_graph.py"
fi
echo

# ================================
# Final Verification
# ================================
log_step "Verifying final state..."

docker compose exec -T -e PGPASSWORD=Fr00pzPlz db psql -U postgres -d divinehaven <<'SQL'
SELECT
  'Verses' as metric,
  COUNT(*)::text as count
FROM verse
UNION ALL
SELECT 'Verse Embeddings', COUNT(*)::text FROM verse_embedding
UNION ALL
SELECT 'Chunk Embeddings', COUNT(*)::text FROM chunk_embedding
UNION ALL
SELECT 'Verse Buckets', COUNT(*)::text FROM verse_bucket
UNION ALL
SELECT 'Bucket Members', COUNT(*)::text FROM verse_bucket_member
UNION ALL
SELECT 'Translations', COUNT(*)::text FROM translation
UNION ALL
SELECT 'Books', COUNT(*)::text FROM book
ORDER BY 1;
SQL

echo
log_success "🎉 Complete pipeline executed successfully!"
echo
echo "📊 Access points:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Neo4j Browser: http://localhost:7474"
echo "   - PostgreSQL: localhost:5432 (user: postgres, db: divinehaven)"
echo
echo "🔄 To rebuild from scratch:"
echo "   docker compose down -v  # ⚠️  DANGER: Deletes all data!"
echo "   ./scripts/shell_scripts/full_pipeline.sh"
echo
echo "📚 Documentation:"
echo "   - MIGRATION_STRATEGY.md - Schema evolution strategy"
echo "   - DATA_PROTECTION.md - Backup and recovery procedures"
