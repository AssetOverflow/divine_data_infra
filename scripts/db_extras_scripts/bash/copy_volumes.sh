#!/bin/bash

declare -A volume_map=(
  ["divinehaven-gpt-guided-build_db_data"]="divinehaven_db_data"
  ["divinehaven-gpt-guided-build_neo4j_data"]="divinehaven_neo4j_data"
  ["divinehaven-gpt-guided-build_neo4j_logs"]="divinehaven_neo4j_logs"
  ["divinehaven-gpt-guided-build_redis_data"]="divinehaven_redis_data"
)

for src in "${!volume_map[@]}"; do
  tgt="${volume_map[$src]}"
  echo "📦 Copying from $src → $tgt"
  docker volume create "$tgt"
  docker run --rm \
    -v "$src:/from" \
    -v "$tgt:/to" \
    alpine sh -c "cp -a /from/. /to/"
done

echo "✅ Volume copy complete."