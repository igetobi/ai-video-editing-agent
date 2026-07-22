#!/usr/bin/env python3
"""Off-ramp — export the cut to a traditional NLE (Premiere / Resolve / FCP).

    python scripts/to_premiere.py --job "channel intro"

Writes premiere/<job>.edl (CMX3600, universal) and premiere/<job>.fcpxml. Import
either into your editor to finish by hand while keeping the agent's cut decisions.
Point the imported timeline at the raw clip in raw/ when prompted to relink media.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib import project  # noqa: E402
from scripts.lib.edl import EDL  # noqa: E402
from scripts.lib.nle_export import build_cmx3600_edl, build_fcpxml  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Export the cut for Premiere/Resolve/FCP.")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()

    job = project.Job.load(args.job)
    if not job.edl_json.is_file():
        print("error: no edl.json — run rough_cut.py first.", file=sys.stderr)
        return 1

    edl = EDL.load(job.edl_json)
    edl_out = job.path("premiere", f"{job.name}.edl")
    fcp_out = job.path("premiere", f"{job.name}.fcpxml")
    edl_out.write_text(build_cmx3600_edl(edl, title=job.name))
    fcp_out.write_text(build_fcpxml(edl, title=job.name, width=job.width, height=job.height))

    print(f"✓ CMX3600 EDL -> {edl_out}")
    print(f"✓ FCPXML      -> {fcp_out}")
    print(f"  raw media   : {job.directory / job.source}")
    print("  Premiere: File > Import, choose the .edl or .fcpxml, then relink to the raw clip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
