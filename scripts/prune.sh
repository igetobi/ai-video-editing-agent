#!/usr/bin/env bash
# prune.sh — reclaim disk by deleting a job's regenerable intermediates.
#
# SAFE by design: only ever removes files that can be rebuilt from the
# source-of-truth artifacts (raw clip, transcript.json, edl.json, plan.json).
# Never touches raw/, the JSON contracts, outputs/, thumbnail/, or premiere/.
#
#   scripts/prune.sh "channel intro"          # prune one job
#   scripts/prune.sh "channel intro" --dry-run
#   scripts/prune.sh --all                    # prune every job
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECTS="$DIR/projects"

DRY=0
TARGETS=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --all) for d in "$PROJECTS"/*/; do [[ -f "$d/job.json" ]] && TARGETS+=("$(basename "$d")"); done ;;
    *) TARGETS+=("$arg") ;;
  esac
done

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "usage: prune.sh <job> [--dry-run] | --all [--dry-run]" >&2
  exit 2
fi

# Intermediates (relative to a job dir) that are cheap to regenerate.
INTERMEDIATES=(
  "transcript/_whisperx"
  "cut/_segments"
  "cut/_concat.txt"
  "cut/_joined.mp4"
  "graphics/segments"
  "graphics/compositions"
  "graphics/.render-cache.json"
  "graphics/composited.mp4"
  "captions/captioned.mp4"
  "music/scored.mp4"
)

reclaim() {
  local job="$1" jobdir="$PROJECTS/$job"
  [[ -d "$jobdir" ]] || { echo "skip: no such job '$job'"; return; }
  echo "pruning: $job"
  for item in "${INTERMEDIATES[@]}"; do
    local p="$jobdir/$item"
    if [[ -e "$p" ]]; then
      local size; size="$(du -sh "$p" 2>/dev/null | cut -f1 || echo '?')"
      if [[ "$DRY" -eq 1 ]]; then
        echo "  would remove ($size) $item"
      else
        rm -rf "$p"
        echo "  removed ($size) $item"
      fi
    fi
  done
}

for t in "${TARGETS[@]}"; do reclaim "$t"; done
[[ "$DRY" -eq 1 ]] && echo "(dry run — nothing deleted)"
echo "done. rebuild any job with: build_graphics.py / captions.py / apply_cuts.py"
