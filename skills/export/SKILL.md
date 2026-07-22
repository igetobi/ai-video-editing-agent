---
name: export
description: Finalize and ship the edit — promote the finished render to outputs/<job>.final.mp4 and copy to Downloads, without deleting project state. Use for "export it", "we're done, finalize", "ship it", "give me the final file". Runs finalize.sh / export.py; prune.sh reclaims disk afterward.
---

# Export (Stage 7)

Promote the finished edit and hand it over. Non-destructive: the whole project stays
intact so the job can be re-opened and re-edited later.

## Run

```
python scripts/export.py --job "<job>"        # or: scripts/finalize.sh "<job>"
```
- Copies the most advanced render (`scored > captioned > composited > rough`) to
  `outputs/<job>.final.mp4` **and** to `~/Downloads` (configurable in
  `config/pipeline.json → export`; `--no-downloads` to skip).
- Verifies and reports the final dimensions/fps/duration.

## After shipping

Offer to reclaim disk (renders can be large):
```
scripts/prune.sh "<job>" --dry-run     # preview what would be deleted
scripts/prune.sh "<job>"               # delete regenerable intermediates only
```
`prune.sh` never removes `raw/`, the JSON contracts, `outputs/`, thumbnails, or the
Premiere export — everything it deletes can be rebuilt from those. Confirm with the
user before pruning a job that isn't finished.

## Do not

Auto-post to social platforms — this system stops at a finished file on disk. If the
user asks to publish, hand them the `outputs/` path.
