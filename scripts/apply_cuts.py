#!/usr/bin/env python3
"""Render an EDL into the rough cut (cut/rough.mp4).

Each kept segment is extracted with a frame-accurate re-encode, the segments are
concatenated, and the result is loudness-normalized for consistent voice level.

Importable: rough_cut.py calls ``render_rough(job, ...)`` after building the EDL.

    python scripts/apply_cuts.py --job "channel intro" [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402
from scripts.lib.edl import EDL  # noqa: E402


def render_rough(job: project.Job, dry_run: bool = False, polish: bool = True) -> Path:
    edl = EDL.load(job.edl_json)
    if not edl.segments:
        raise RuntimeError("EDL has no segments — nothing to render.")
    src = job.directory / edl.source

    seg_dir = job.path("cut", "_segments")
    seg_dir.mkdir(parents=True, exist_ok=True)
    concat_list = job.path("cut", "_concat.txt")

    lines = []
    for seg in edl.segments:
        out = seg_dir / f"{seg.id}.mp4"
        ffmpeg.run(ffmpeg.extract_segment(src, out, seg.src_in, seg.src_out), dry_run=dry_run)
        lines.append(f"file '{out.resolve()}'")
    if not dry_run:
        concat_list.write_text("\n".join(lines) + "\n")

    joined = job.path("cut", "_joined.mp4") if polish else job.rough_mp4
    ffmpeg.run(ffmpeg.concat_demux(concat_list, joined, reencode=False), dry_run=dry_run)

    if polish:
        target = float(presets.load_json(presets._config_dir() / "pipeline.json", {})
                       .get("rough_cut", {}).get("audio_target_lufs", -16.0))
        ffmpeg.run(ffmpeg.loudnorm(joined, job.rough_mp4, i=target), dry_run=dry_run)

    if not dry_run:
        job.set_stage("rough_cut", "done",
                      segments=len(edl.segments),
                      timeline_duration=round(edl.timeline_duration, 2))
    return job.rough_mp4


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the EDL into cut/rough.mp4.")
    ap.add_argument("--job", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-polish", action="store_true", help="Skip loudness normalization.")
    args = ap.parse_args()

    job = project.Job.load(args.job)
    out = render_rough(job, dry_run=args.dry_run, polish=not args.no_polish)
    print(f"✓ rough cut rendered -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
