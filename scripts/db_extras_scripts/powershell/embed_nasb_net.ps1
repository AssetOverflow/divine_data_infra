uv run python .\manifest_cli.py embed-verses `
  --model=embeddinggemma --dim=768 --dsn="$env:DSN" `
  --translation=NASB --translation=NET `
  --reembed `
  --batch=128 --workers=12 --keep-alive=10m

