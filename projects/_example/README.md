# projects/ — one folder per job

Every edit is a self-contained job directory here, created by `intake.py`. Real jobs
are git-ignored (they hold big media); this `_example/` shows the layout.

```
projects/<job>/
  job.json                     # manifest + per-stage status (source of truth)
  raw/<clip>                   # your original footage — never modified
  transcript/
    transcript.json            # WhisperX word-level output (normalized)
    corrected.json             # + brand/spelling corrections applied
  cut/
    edl.json                   # THE CUT — kept source spans + word indices (editable)
    rough.mp4                  # rendered rough cut
  graphics/
    plan.json                  # THE GRAPHICS — beats (editable)
    compositions/<beat>.html   # generated HyperFrames compositions (disposable)
    segments/<beat>.mov        # rendered per-beat alpha overlays
    .render-cache.json         # incremental-render hashes
    composited.mp4             # cut + graphics
  captions/
    captions.ass               # word-level caption track
    captioned.mp4              # + captions (short-form)
  music/scored.mp4             # + background music (optional)
  thumbnail/<job>.png          # thumbnail (if generated)
  premiere/<job>.edl|.fcpxml   # NLE off-ramp (if exported)
  outputs/<job>.final.mp4      # the shipped file
```

To edit an existing job, change the **editable** files (`edl.json`, `plan.json`, or
the brand tokens) and re-run the relevant stage. To reclaim disk after shipping, run
`scripts/prune.sh "<job>"` — it deletes only the regenerable intermediates.
