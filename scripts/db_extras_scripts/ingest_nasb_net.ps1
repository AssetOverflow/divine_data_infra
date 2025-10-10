# NASB
uv run python .\manifest_cli.py ingest `
  --json .\unified_json_bibles\en_nasb.universal.json `
  --translation NASB `
  --language en `
  --source-version divine_haven.universal_v1 `
  --dsn "$env:DSN"

# NET
uv run python .\manifest_cli.py ingest `
  --json .\unified_json_bibles\en_net.universal.json `
  --translation NET `
  --language en `
  --source-version divine_haven.universal_v1 `
  --dsn "$env:DSN"

