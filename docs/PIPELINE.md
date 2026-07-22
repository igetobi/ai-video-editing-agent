# The pipeline in depth

Seven stages. The same seven for every job; only **3 (graphics)** and **5 (captions)**
change per format. Each stage reads and writes plain JSON so you can inspect or edit
anything by hand.

## 1 · Intake — `intake.py`

Creates `projects/<job>/`, copies the raw clip into `raw/` (never moves it), probes
dimensions/fps (ffprobe), and writes the `job.json` manifest. Choose a format here;
it decides steps 3 & 5.

## 2 · Rough cut — `transcribe.py` → `rough_cut.py`

**Transcribe** with WhisperX → normalized `transcript/transcript.json`, then apply
`presets/caption-corrections.json` → `transcript/corrected.json`. Word-level timings
are the foundation for everything downstream.

**Cut** (`rough_cut.py`) builds `cut/edl.json` — the list of kept source spans:
- A "span" is a run of kept words whose gaps stay under `min_gap`; wherever a gap
  exceeds it (a pause), the span closes → silence is dropped automatically.
- Hesitations (um/uh/erm) are removed as words. Discourse fillers (like/basically) are
  **flagged in each segment's note**, not auto-cut (use `--aggressive` to cut them).
- Kept spans get a little lead/tail padding so cuts don't clip consonants; near-adjacent
  spans merge for smoother audio.

Then it renders `cut/rough.mp4` (frame-accurate segment extraction → concat →
loudness normalize). Edit `edl.json` and re-render with `apply_cuts.py` — no
re-analysis. **Lock the rough cut before graphics** (beats are timed to it).

## 3 · Graphics — `plan_graphics.py` → `build_graphics.py` *(format-specific)*

`plan_graphics.py` scaffolds `graphics/plan.json`: correctly-timed placeholder
**beats** for the format. A beat = a timeline span + a `kind` (lower-third, top-card,
hook-card, callout, list, quote, stat, b-roll, logo-bug, zoom, transition) + copy +
`preset`. The `graphics-plan` skill rewrites the copy/kinds/assets to be *good*.

`build_graphics.py` turns each beat into a HyperFrames composition (`engine/`), renders
it, and composites overlays (+ ken-burns `zoom` beats) onto the cut →
`graphics/composited.mp4`. **Incremental:** a per-beat content hash
(`graphics/.render-cache.json`) means only changed beats re-render.

## 4 · Second pass — `build_graphics.py --only <ids>` *(manual, with you)*

The refinement loop. React to a beat → edit it in `plan.json` → rebuild just that beat
in seconds → look again. See `PROMPTING.md` for phrase→edit mappings.

## 5 · Captions — `captions.py` *(short-form only, format-specific)*

Burns word-level captions that appear on-beat, remapped onto the **edited** timeline
via the EDL (no re-transcription). Rendered as an ASS track and burned in one ffmpeg
pass → `captions/captioned.mp4`. Explainer = centered/locked; TikTok = low/bold.
Long-form skips this (YouTube CC) unless `--force`.

## 6 · Background music — `background_music.py` *(optional)*

Mixes a track under the voice with side-chain ducking (music dips when you speak) and
re-normalizes the whole mix → `music/scored.mp4`. `--gain -23` is a barely-there bed.

## 7 · Export — `export.py` / `finalize.sh`

Promotes the most advanced render to `outputs/<job>.final.mp4` and copies to
Downloads. Non-destructive — the project stays fully re-editable. `prune.sh` then
reclaims disk by deleting only regenerable intermediates.

## Off-ramp · to-premiere — `to_premiere.py`

Any time after stage 2: exports `premiere/<job>.edl` (CMX3600) and `.fcpxml` to finish
by hand in Premiere/Resolve/FCP. Relink to the raw clip in `raw/`.

## Data contracts (edit these)

| File | What it is | Edit to… |
|------|-----------|----------|
| `job.json` | Job manifest / stage status | change format, dims, fps |
| `transcript/corrected.json` | Word-level transcript | fix a word before it hits script/captions |
| `cut/edl.json` | The cut list | change what's kept, pad/trim/split cuts |
| `graphics/plan.json` | The graphics | move/retime/restyle/add beats |
| `config/brand.tokens.json` | Identity | rebrand everything at once |
