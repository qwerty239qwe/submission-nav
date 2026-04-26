#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if ! command -v uv >/dev/null 2>&1; then
  echo "Missing required helper runtime: uv" >&2
  echo "Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

echo "Preparing local helper environment..."
(
  cd "$SCRIPT_DIR"
  uv sync
)

ENV_EXAMPLE="$REPO_ROOT/.env.example"
ENV_FILE="$REPO_ROOT/.env"
if [ -f "$ENV_EXAMPLE" ] && [ ! -f "$ENV_FILE" ]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Created repo-local .env from .env.example"
fi

echo "Helper runtime is ready."
