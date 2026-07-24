#!/usr/bin/env python3
"""Stage 3a — Graphics plan. Scaffold graphics/plan.json from the cut + transcript.

    python scripts/plan_graphics.py --job "channel intro"

Writes placeholder beats with correct timing for the job's format. The graphics-plan
skill then rewrites the copy/kinds/assets. After editing the plan, run build_graphics.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import presets, project  # noqa: E402
from scripts.lib.edl import EDL  # noqa: E402
from scripts.lib.planning import build_plan  # noqa: E402
from scripts.lib.transcript import Transcript  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold the graphics plan.")
    ap.add_argument("--job")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing plan.json.")
    args = ap.parse_args()

    job = project.load_job(args.job)
    if job.plan_json.is_file() and not args.force:
        print(f"plan already exists: {job.plan_json} (use --force to regenerate)")
        return 0

    edl = EDL.load(job.edl_json)
    tpath = job.corrected_json if job.corrected_json.is_file() else job.transcript_json
    t = Transcript.load(tpath)
    fmt = presets.load_format(job.format)
    bpm = presets.load_json(presets._config_dir() / "pipeline.json", {}).get("graphics", {}).get("beats_per_minute_target", 8)

    plan = build_plan(edl, t, fmt, job.format, job.width, job.height, job.fps, bpm_target=bpm)
    plan.save(job.plan_json)

    job.set_stage("graphics", "planned", beats=len(plan.beats))
    print(f"✓ scaffolded {len(plan.beats)} beats -> {job.plan_json}")
    print("  refine copy/kinds/assets in that file (or ask the graphics-plan skill), then:")
    print("  python scripts/build_graphics.py --job", job.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
