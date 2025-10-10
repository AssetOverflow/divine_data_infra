#!/usr/bin/env bash
set -euo pipefail

# Ensure Astral uv
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing Astral uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Sync environment
uv python install 3.11
uv venv --seed .venv
uv pip install --upgrade pip
uv sync

# Print summary
. .venv/bin/activate
python -V
uv pip list