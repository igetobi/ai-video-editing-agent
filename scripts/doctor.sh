#!/usr/bin/env bash
# doctor.sh — check that everything the pipeline needs is installed.
#
#   scripts/doctor.sh
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ok=0; warn=0; fail=0
green() { printf "  \033[32m✓\033[0m %s\n" "$1"; ok=$((ok+1)); }
yellow(){ printf "  \033[33m•\033[0m %s\n" "$1"; warn=$((warn+1)); }
red()   { printf "  \033[31m✗\033[0m %s\n" "$1"; fail=$((fail+1)); }

echo "AI video editing agent — environment check"
echo

echo "Required:"
if command -v python3 >/dev/null; then green "python3 $(python3 --version 2>&1 | awk '{print $2}')"; else red "python3 missing"; fi
if command -v ffmpeg  >/dev/null; then green "ffmpeg  $(ffmpeg -version | head -1 | awk '{print $3}')"; else red "ffmpeg missing  ->  macOS: brew install ffmpeg"; fi
if command -v ffprobe >/dev/null; then green "ffprobe present"; else red "ffprobe missing (ships with ffmpeg)"; fi
if command -v node    >/dev/null; then
  v="$(node --version | tr -d 'v')"; major="${v%%.*}"
  if [[ "$major" -ge 22 ]]; then green "node $v"; else red "node $v (HyperFrames needs >= 22  ->  nvm install 22)"; fi
else red "node missing  ->  install Node 22+ (nvm install 22)"; fi
if command -v npx     >/dev/null; then green "npx present"; else red "npx missing (ships with node)"; fi

echo
echo "Transcription:"
if command -v whisperx >/dev/null; then green "whisperx present";
else yellow "whisperx missing  ->  pipx install whisperx   (or: pip install whisperx)"; fi

echo
echo "Engine (HyperFrames):"
if [[ -f "$DIR/package.json" ]] && [[ -d "$DIR/node_modules/hyperframes" || -d "$DIR/node_modules/.bin" ]]; then
  green "hyperframes installed locally"
elif command -v npx >/dev/null; then
  yellow "hyperframes not vendored locally — 'npx hyperframes' will fetch on first use"
  yellow "install skills:  npx skills add heygen-com/hyperframes --full-depth"
fi

echo
echo "Assets (optional but recommended):"
[[ -f "$DIR/assets/fonts/Coolvetica.otf" ]] && green "caption font present" || yellow "drop a display/caption font in assets/fonts/ (demo uses Coolvetica)"
[[ -f "$DIR/config/brand.tokens.json" ]] && green "brand tokens present" || yellow "config/brand.tokens.json missing"

echo
echo "Summary: $ok ok, $warn warnings, $fail blocking"
if [[ "$fail" -gt 0 ]]; then
  echo "Fix the ✗ items above, then re-run. See docs/SETUP.md."
  exit 1
fi
echo "You're ready. Start with:  python3 scripts/intake.py --source <clip> --name <title> --format <fmt>"
