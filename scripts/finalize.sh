#!/usr/bin/env bash
# finalize.sh — promote a job's finished edit to outputs/<job>.final.mp4
# (and to Downloads, per config). Thin wrapper around export.py.
#
#   scripts/finalize.sh "channel intro"
#   scripts/finalize.sh "channel intro" --no-downloads
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: finalize.sh <job> [--no-downloads|--to-downloads]" >&2
  exit 2
fi

JOB="$1"; shift || true
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$DIR/scripts/export.py" --job "$JOB" "$@"
