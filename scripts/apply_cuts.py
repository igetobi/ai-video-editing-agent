#!/usr/bin/env python3
"""Render an EDL into the rough cut (cut/rough.mp4).

Single-pass, frame-accurate trim+concat straight from the source (trim/atrim
filters, not -ss seeking), so cuts land exactly on the word-level timestamps. Seams
are cross-dissolved by default (config render.smooth_cuts) so talking-head cuts read
smooth instead of hard-jumping, then the voice is loudness-normalized.

Importable: rough_cut.py calls ``render_rough(job, ...)`` after building the EDL.

    python scripts/apply_cuts.py [--job "channel intro"] [--hard-cuts] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402
from scripts.lib.edl import EDL  # noqa: E402


def render_rough(job: project.Job, dry_run: bool = False, polish: bool = True,
                 smooth: bool | None = None) -> Path:
    edl = EDL.load(job.edl_json)
    if not edl.segments:
        raise RuntimeError("EDL has no segments — nothing to render.")
    src = job.directory / edl.source
    spans = [(s.src_in, s.src_out) for s in edl.segments]

    cfg = presets.load_json(presets._config_dir() / "pipeline.json", {})
    rcfg = cfg.get("render", {})
    if smooth is None:
        smooth = bool(rcfg.get("smooth_cuts", True))
    transition = float(rcfg.get("transition_sec", 0.13))

    has_audio = True
    if not dry_run and ffmpeg.have("ffprobe"):
        try:
            has_audio = ffmpeg.probe(src).has_audio
        except ffmpeg.FFmpegError:
            has_audio = True

    joined = job.path("cut", "_joined.mp4") if polish else job.rough_mp4
    if smooth and len(spans) > 1 and has_audio:
        cmd = ffmpeg.trim_concat_smooth(src, spans, joined, edl.fps, transition=transition)
    else:
        cmd = ffmpeg.trim_concat(src, spans, joined, edl.fps, has_audio=has_audio)
    ffmpeg.run(cmd, dry_run=dry_run)

    if polish:
        target = float(cfg.get("rough_cut", {}).get("audio_target_lufs", -16.0))
        ffmpeg.run(ffmpeg.loudnorm(joined, job.rough_mp4, i=target), dry_run=dry_run)

    if not dry_run:
        job.set_stage("rough_cut", "done", segments=len(edl.segments),
                      timeline_duration=round(edl.timeline_duration, 2),
                      smooth=bool(smooth and len(spans) > 1 and has_audio))
    return job.rough_mp4


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the EDL into cut/rough.mp4.")
    ap.add_argument("--job")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--hard-cuts", action="store_true", help="Disable seam cross-dissolves.")
    ap.add_argument("--no-polish", action="store_true", help="Skip loudness normalization.")
    args = ap.parse_args()

    job = project.load_job(args.job)
    out = render_rough(job, dry_run=args.dry_run, polish=not args.no_polish,
                       smooth=False if args.hard_cuts else None)
    print(f"✓ rough cut rendered -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
