#!/usr/bin/env bash
set -euo pipefail

MANIFEST_PATH=${1:-manifest.json}

# Activate virtual environment
. .venv/bin/activate

# Generate the indexes SQL
python manifest_cli.py plan-indexes "$MANIFEST_PATH" postgres > .tmp.indexes.sql

# Apply the indexes SQL to the database
docker exec -i divinehaven-backend-db psql -U postgres -d divinehaven -v ON_ERROR_STOP=1 < .tmp.indexes.sql