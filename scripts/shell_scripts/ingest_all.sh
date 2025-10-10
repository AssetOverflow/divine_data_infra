#!/usr/bin/env bash
set -euo pipefail

# ================================
# DivineHaven – Ingest all Bibles
# ================================

# Override via env if desired
BIBLES_DIR="${BIBLES_DIR:-/mnt/d/os-agnostic-fs/divinehaven-gpt-guided-build/unified_json_bibles}"
DSN="${DSN:-postgresql://postgres:postgres@localhost:5432/divinehaven}"
SOURCE_VERSION="${SOURCE_VERSION:-divine_haven.universal_v1}"

# Preflight
if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: \`uv\` is not on PATH. Install uv (https://docs.astral.sh/uv/) or adjust the script to use python." >&2
  exit 1
fi
if [[ ! -f "manifest_cli.py" ]]; then
  echo "ERROR: manifest_cli.py not found in current directory: $(pwd)" >&2
  exit 1
fi
if [[ ! -d "$BIBLES_DIR" ]]; then
  echo "ERROR: BIBLES_DIR does not exist: $BIBLES_DIR" >&2
  exit 1
fi

# Map translation code -> "filename:language"
declare -A files=(
  [ASV]="en_asv.universal.json:en"
  [ESV]="en_esv.universal.json:en"
  [KJV]="en_kjv.universal.json:en"
  [NASB]="en_nasb.universal.json:en"
  [NASU]="en_nasu.universal.json:en"
  [NET]="en_net.universal.json:en"
  [NIRV]="en_nirv.universal.json:en"
  [NIV]="en_niv.universal.json:en"
  [NKJV]="en_nkjv.universal.json:en"
  [NLT]="en_nlt.universal.json:en"
  [NVI]="spanish_nvi_bible.universal.json:es"
  [RVR1960]="spanish_rvr1960_bible.universal.json:es"
  [LXX]="septuagint_lxx_complete.universal.json:el"
  [TNK]="he_tanakh.universal.json:he"
)

# Order you want to ingest in (kept from your script)
order=(NIV ESV NLT KJV NKJV ASV NASU NIRV RVR1960 NVI LXX TNK NASB NET)

echo "📚 BIBLES_DIR = $BIBLES_DIR"
echo "🗄️  DSN        = $DSN"
echo "🏷️  SOURCE_VER = $SOURCE_VERSION"
echo

have_psql=false
if command -v psql >/dev/null 2>&1; then
  have_psql=true
fi

for code in "${order[@]}"; do
  entry="${files[$code]:-}"
  if [[ -z "$entry" ]]; then
    echo "WARN: no mapping for $code; skipping"
    continue
  fi

  IFS=: read -r rel lang <<< "$entry"
  f="$BIBLES_DIR/$rel"
  if [[ ! -f "$f" ]]; then
    echo "WARN: missing file $f; skipping $code"
    continue
  fi

  echo "→ Ingesting $code ($lang) from $rel"
  start=$(date +%s)

  uv run python manifest_cli.py ingest \
    --json "$f" \
    --translation "$code" \
    --language "$lang" \
    --source-version "$SOURCE_VERSION" \
    --dsn "$DSN"

  dur=$(( $(date +%s) - start ))
  echo "✓ $code done in ${dur}s"

  # Optional per-translation sanity counts if psql is present
  if $have_psql; then
    echo "   ├─ books:   $(psql "$DSN" -At -c "SELECT count(*) FROM book WHERE translation_code='${code}'")"
    echo "   └─ verses:  $(psql "$DSN" -At -c "SELECT count(*) FROM verse WHERE translation_code='${code}'")"
  fi
done

echo "✅ Ingest complete."
