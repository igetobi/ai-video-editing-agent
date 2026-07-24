#!/usr/bin/env python3
"""Stage 7 — Export. Promote the finished edit to outputs/<job>.final.mp4.

    python scripts/export.py --job "channel intro" [--to-downloads]

Copies the most advanced render (scored > captioned > composited > rough) to
outputs/<job>.final.mp4 and, if configured, also to your Downloads folder — without
deleting any project state, so you can always re-open and re-edit the job.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote the final render.")
    ap.add_argument("--job")
    ap.add_argument("--to-downloads", action="store_true", help="Force-copy to Downloads.")
    ap.add_argument("--no-downloads", action="store_true", help="Skip the Downloads copy.")
    args = ap.parse_args()

    job = project.load_job(args.job)
    latest = job.latest_video()
    if latest is None:
        print("error: nothing rendered yet.", file=sys.stderr)
        return 1

    job.final_mp4.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest, job.final_mp4)
    print(f"✓ exported ({latest.name}) -> {job.final_mp4}")

    cfg = presets.load_json(presets._config_dir() / "pipeline.json", {}).get("export", {})
    want_dl = (cfg.get("also_copy_to_downloads", True) or args.to_downloads) and not args.no_downloads
    if want_dl:
        dl = Path(cfg.get("downloads_dir", "~/Downloads")).expanduser()
        if dl.is_dir():
            dest = dl / job.final_mp4.name
            shutil.copy2(job.final_mp4, dest)
            print(f"✓ copied to Downloads -> {dest}")
        else:
            print(f"  (Downloads dir {dl} not found; skipped)")

    if ffmpeg.have("ffprobe"):
        try:
            info = ffmpeg.probe(job.final_mp4)
            print(f"  final: {info.width}x{info.height} @ {info.fps}fps, {info.duration:.1f}s, audio={info.has_audio}")
        except ffmpeg.FFmpegError:
            pass

    job.set_stage("export", "done", final=str(job.final_mp4))
    print("  ship it 🚀  (run scripts/prune.sh to reclaim disk from intermediates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
