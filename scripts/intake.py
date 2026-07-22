#!/usr/bin/env python3
"""Stage 1 — Intake. Create a job and copy the raw clip in.

    python scripts/intake.py --source /path/to/raw.mp4 --name "channel intro" --format long-form

The raw clip is copied (never moved) into projects/<job>/raw/ so the original is
untouched. Dimensions/fps are probed from the clip when ffprobe is available and
default to the format's spec otherwise.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a job and ingest a raw clip.")
    ap.add_argument("--source", required=True, help="Path to the raw footage.")
    ap.add_argument("--name", help="Job title (defaults to the file name).")
    ap.add_argument("--format", default="long-form", help="long-form | short-explainer | short-tiktok")
    args = ap.parse_args()

    src = Path(args.source).expanduser()
    if not src.is_file():
        print(f"error: source not found: {src}", file=sys.stderr)
        return 1

    try:
        fmt = presets.load_format(args.format)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    name = args.name or src.stem
    job = project.Job.create(name, fmt=args.format)
    job.width = int(fmt["width"])
    job.height = int(fmt["height"])
    job.fps = float(fmt["fps"])

    dest = job.path("raw", src.name)
    shutil.copy2(src, dest)
    job.source = f"raw/{src.name}"

    if ffmpeg.have("ffprobe"):
        try:
            info = ffmpeg.probe(dest)
            job.meta["probe"] = {
                "duration": info.duration, "width": info.width,
                "height": info.height, "fps": info.fps, "has_audio": info.has_audio,
            }
            if info.fps:
                job.fps = info.fps
        except ffmpeg.FFmpegError as e:
            print(f"warn: ffprobe failed ({e}); using format defaults.", file=sys.stderr)

    job.set_stage("intake", "done", source=job.source)
    print(f"✓ intake: job '{job.name}' [{args.format}] {job.width}x{job.height}@{job.fps}fps")
    print(f"  dir: {job.directory}")
    print(f"  raw: {dest}")
    print("  next: python scripts/transcribe.py --job", job.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
