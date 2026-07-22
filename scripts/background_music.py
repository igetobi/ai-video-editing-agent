#!/usr/bin/env python3
"""Stage 6 — Background music (optional). Mix a track under the voice with ducking.

    python scripts/background_music.py --job "channel intro" --music /path/melting-glass.mp3 --gain -23

The music sits at ``--gain`` dB and side-chain ducks further whenever you're
speaking, then the whole mix is re-normalized to broadcast loudness. -23 dB is a
good "barely there" bed; raise toward -18 for a more present track.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import ffmpeg, presets, project  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Add ducked background music.")
    ap.add_argument("--job", required=True)
    ap.add_argument("--music", required=True, help="Path to the music file.")
    ap.add_argument("--gain", type=float, help="Resting music level in dB (default from pipeline.json).")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    job = project.Job.load(args.job)
    music = Path(args.music).expanduser()
    if not music.is_file():
        print(f"error: music not found: {music}", file=sys.stderr)
        return 1

    base = job.latest_video()
    if base is None:
        print("error: no rendered video yet (need at least a rough cut).", file=sys.stderr)
        return 1

    cfg = presets.load_json(presets._config_dir() / "pipeline.json", {}).get("music", {})
    gain = args.gain if args.gain is not None else float(cfg.get("default_gain_db", -23.0))

    # Keep a copy of the track with the job for reproducibility.
    if not args.dry_run:
        shutil.copy2(music, job.path("music", music.name))

    ffmpeg.run(
        ffmpeg.add_music_ducked(base, music, job.scored_mp4,
                                music_gain_db=gain,
                                duck_threshold=float(cfg.get("duck_threshold", 0.05))),
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        job.set_stage("music", "done", track=music.name, gain_db=gain)
        print(f"✓ music mixed at {gain} dB (ducked) -> {job.scored_mp4}")
        print("  next: python scripts/export.py --job", job.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
