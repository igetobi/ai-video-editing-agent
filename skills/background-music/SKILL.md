---
name: background-music
description: Add a background music bed under the voice, side-chain ducked and re-normalized. Use for "add background music", "put this song under it", "add a music track". Optional step. Point it at a music file and optionally set the level in dB.
---

# Background music (Stage 6) — optional

Lay a music bed under the voice. The music ducks automatically whenever you speak,
then the whole mix is re-normalized to a consistent loudness.

## Run

```
python scripts/background_music.py --job "<job>" --music "<path to song>" --gain -23
```
- `--gain` is the resting music level in dB. **-23** ≈ barely-there bed (great under
  narration); **-18** is more present. Default from `config/pipeline.json → music`.
- Applies to the current best render (captioned > composited > rough) → `music/scored.mp4`.
- A copy of the track is saved into `music/` for reproducibility.

## Guidance

- Start quiet and raise if asked. It's easy to overpower a voice.
- If the user names a track by vibe ("something chill"), ask for the file path — this
  step doesn't source music, it mixes a file you point it at.
- Ducking params (threshold/ratio) are in `config/pipeline.json`; the defaults suit
  most spoken-word content.

## Then

**export** to ship.
