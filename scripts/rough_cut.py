#!/usr/bin/env python3
"""Stage 2b — Rough cut. Build the EDL from the transcript, then render it.

    python scripts/rough_cut.py --job "channel intro" [--aggressive] [--no-render] [--dry-run]

The EDL (cut/edl.json) is the reviewable, editable source of truth. Re-run
apply_cuts.py after hand/agent-editing it to re-render without re-analyzing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import presets, project  # noqa: E402
from scripts.lib.cutting import build_edl  # noqa: E402
from scripts.lib.transcript import Transcript  # noqa: E402
from scripts.apply_cuts import render_rough  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Build + render the rough cut.")
    ap.add_argument("--job", required=True)
    ap.add_argument("--aggressive", action="store_true", help="Also cut discourse fillers (like/basically/actually).")
    ap.add_argument("--no-render", action="store_true", help="Write edl.json only; don't render.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    job = project.Job.load(args.job)
    tpath = job.corrected_json if job.corrected_json.is_file() else job.transcript_json
    if not tpath.is_file():
        print("error: no transcript. Run transcribe.py first.", file=sys.stderr)
        return 1

    t = Transcript.load(tpath)
    cfg = presets.load_json(presets._config_dir() / "pipeline.json", {}).get("rough_cut", {})
    if args.aggressive:
        cfg = {**cfg, "aggressive_filler": True}

    edl = build_edl(t, source=job.source, cfg=cfg, fps=job.fps)
    edl.save(job.edl_json)

    m = edl.meta
    print(f"✓ EDL built: {edl.summary()}")
    print(f"  source {m['source_duration']:.1f}s -> timeline {m['timeline_duration']:.1f}s "
          f"(removed {m['removed']:.1f}s)")
    flagged = [s.id for s in edl.segments if s.note]
    if flagged:
        print(f"  flagged for review ({len(flagged)}): {', '.join(flagged[:8])}"
              + (" ..." if len(flagged) > 8 else ""))
    print(f"  edit here: {job.edl_json}")

    if args.no_render:
        print("  (skipped render) next: python scripts/apply_cuts.py --job", job.name)
        return 0

    out = render_rough(job, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"✓ rough cut -> {out}")
        print("  review it, then: python scripts/plan_graphics.py --job", job.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
