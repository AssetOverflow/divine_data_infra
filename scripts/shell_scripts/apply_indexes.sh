#!/usr/bin/env bash
set -euo pipefail

MANIFEST_PATH=${1:-manifest.json}
. .venv/bin/activate
python manifest_cli.py plan-indexes "$MANIFEST_PATH" postgres > .tmp.indexes.sql
docker exec -i -w / divinehaven-db psql -U postgres -d divinehaven -v ON_ERROR_STOP=1 -f /dev/stdin < .tmp.ddl.sql
