#!/usr/bin/env sh
set -eu

BIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$BIN_DIR/.." && pwd)
SETUP_SCRIPT="$REPO_ROOT/scripts/setup.sh"

if [ ! -f "$SETUP_SCRIPT" ]; then
  echo "Missing setup script: $SETUP_SCRIPT" >&2
  exit 1
fi

echo "submission-nav setup"
echo "Repository: $REPO_ROOT"

sh "$SETUP_SCRIPT"

echo
echo "submission-nav is ready. Restart your agent host if it is already running."
