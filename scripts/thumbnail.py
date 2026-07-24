#!/usr/bin/env python3
"""Thumbnail generator. Grab a hero frame and optionally overlay a title.

    python scripts/thumbnail.py --job "channel intro" --time 3.2 --title "I automated my editing"

Grabs a high-quality frame at --time from the most advanced render, then (if a title
is given) overlays punchy text using the brand display font. Output: thumbnail/<job>.png.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a thumbnail.")
    ap.add_argument("--job")
    ap.add_argument("--time", type=float, default=1.0, help="Timestamp (s) of the hero frame.")
    ap.add_argument("--title", help="Optional overlay title.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    job = project.load_job(args.job)
    base = job.latest_video() or (job.directory / job.source)
    if not Path(base).is_file() and not args.dry_run:
        print(f"error: no source video for thumbnail: {base}", file=sys.stderr)
        return 1

    out = job.path("thumbnail", f"{job.name}.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    if not args.title:
        ffmpeg.run(ffmpeg.thumbnail_frame(Path(base), out, args.time), dry_run=args.dry_run)
    else:
        brand = presets.load_brand()
        font_url = brand.get("font", {}).get("display_url", "")
        font_path = project.repo_root() / font_url if font_url else None
        accent = brand.get("color", {}).get("accent", "#E07A3F")
        title = args.title.replace(":", r"\:").replace("'", r"\\'")
        fontfile = f":fontfile={font_path}" if font_path and Path(font_path).is_file() else ""
        vf = (
            f"drawtext=text='{title}'{fontfile}:fontcolor=white:fontsize=h/9:"
            f"box=1:boxcolor={accent}@0.85:boxborderw=28:"
            f"x=(w-text_w)/2:y=h-(h/4)"
        )
        cmd = ["ffmpeg", "-y", "-ss", f"{args.time:.3f}", "-i", str(base),
               "-frames:v", "1", "-vf", vf, "-q:v", "2", str(out)]
        ffmpeg.run(cmd, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"✓ thumbnail -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
