---
name: intake
description: Start a new video editing job from a raw clip. Use when the user drops in raw footage, gives a file path to a video, or says "start a new project / new video / edit this clip". Creates projects/<job>/ and copies the raw file in.
---

# Intake (Stage 1)

Create a job and bring the raw footage under management. Nothing is edited yet.

## Steps

1. Determine the **format** if the user didn't say:
   - Horizontal / YouTube / "long-form" → `long-form`
   - Vertical explainer with your face + top graphics → `short-explainer`
   - Vertical raw/punchy TikTok/Reel → `short-tiktok`
   If ambiguous, ask once (it decides steps 3 & 5).
2. Pick a short job name from the content ("channel intro", "saas demo").
3. Run:
   ```
   python scripts/intake.py --source "<path to raw clip>" --name "<job>" --format <format>
   ```
4. Confirm the reported dimensions/fps look right. The raw clip is **copied** into
   `projects/<job>/raw/` — the original is never touched.

## Then

Move to the **rough-cut** skill: `python scripts/transcribe.py --job "<job>"`.

Notes: the file path can be pasted directly (e.g. from Finder ⌥⌘C). `~` is expanded.
If the user has several clips, do one job per deliverable video.
