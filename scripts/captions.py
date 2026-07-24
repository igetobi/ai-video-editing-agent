#!/usr/bin/env python3
"""Stage 5 — Captions. Burn word-level animated captions into short-form videos.

    python scripts/captions.py --job "tiktok clip" [--position low|center|top] [--force]

Captions follow the *edited* timeline (they use the EDL to remap word timings), and
reuse the existing WhisperX word timestamps — no re-transcription. Long-form skips
this by default (ships with YouTube CC); pass --force to caption it anyway.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402
from scripts.lib.captions_ass import build_ass  # noqa: E402
from scripts.lib.edl import EDL  # noqa: E402
from scripts.lib.planning import _timeline_words  # noqa: E402
from scripts.lib.transcript import Transcript, Word  # noqa: E402


def timeline_caption_words(job: project.Job) -> list[Word]:
    edl = EDL.load(job.edl_json)
    tpath = job.corrected_json if job.corrected_json.is_file() else job.transcript_json
    t = Transcript.load(tpath)
    return [Word(text=txt, start=ti, end=to) for (ti, to, txt) in _timeline_words(edl, t)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Burn animated captions into the video.")
    ap.add_argument("--job")
    ap.add_argument("--position", help="Override caption position (low|center|top|0..1).")
    ap.add_argument("--preset", help="Override the caption preset name.")
    ap.add_argument("--force", action="store_true", help="Caption even if the format disables it.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    job = project.load_job(args.job)
    fmt = presets.load_format(job.format)
    cap_cfg = fmt.get("captions", {})
    if not cap_cfg.get("enabled", False) and not args.force:
        print(f"format '{job.format}' has captions disabled ({cap_cfg.get('note', '')}). Use --force to override.")
        return 0

    preset_name = args.preset or cap_cfg.get("preset", "captions-style")
    style, _ = presets.resolve_style(preset_name)
    position = args.position or cap_cfg.get("position") or style.get("position", "center")

    words = timeline_caption_words(job)
    if not words:
        print("error: no words to caption (empty transcript/EDL).", file=sys.stderr)
        return 1

    ass = build_ass(words, style, job.width, job.height, position_override=position)
    if not args.dry_run:
        job.captions_ass.write_text(ass)
    print(f"✓ caption track: {len(words)} words, position={position} -> {job.captions_ass}")

    base = job.composited_mp4 if job.composited_mp4.is_file() else job.rough_mp4
    fonts_dir = project.repo_root() / "assets" / "fonts"
    ffmpeg.run(
        ffmpeg.burn_subtitles(base, job.captions_ass, job.captioned_mp4, fonts_dir=fonts_dir),
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        job.set_stage("captions", "done", words=len(words), position=position)
        print(f"✓ captions burned -> {job.captioned_mp4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
