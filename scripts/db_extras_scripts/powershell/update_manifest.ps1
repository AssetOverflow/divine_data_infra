uv run python .\manifest_cli.py init `
  --embedding-model=embeddinggemma `
  --embedding-dim=768 `
  --translations=NIV --translations=ESV translations=NLT --translations=KJV --translations=NKJV --translations=ASV --translations=NASU --translations=NIRV --translations=RVR1960 --translations=NVI --translations=LXX --translations=TNK --translations=NASB --translations=NET `
  --languages=en --languages=es --languages=el --languages=he `
  --pipeline-version=embed-pipeline@1.2.0 `
  --source-version=divine_haven.universal_v1 `
  --overwrite

