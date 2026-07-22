# Deploying to Railway

You can run this on [Railway](https://railway.com) — it's a good home for the **heavy
compute** (transcription + rendering) if your laptop struggles with the installs. Two
things to understand first so you don't fight the platform:

1. **This is a batch/interactive CLI tool, not a web server.** There's no HTTP
   endpoint to serve. On Railway you drive it from the **shell** (or one-off
   commands), not a browser.
2. **Railway containers are ephemeral.** Anything written to disk is lost on redeploy
   unless you attach a **Volume**. Your `projects/` (job data + renders) must live on a
   Volume, or be pushed to object storage.

## Deploy from this repo

1. Push this repo to GitHub (already done on your branch).
2. In Railway: **New Project → Deploy from GitHub repo** → pick this repo.
3. Railway reads `railway.json` and builds the **Dockerfile** (all deps baked in:
   ffmpeg, Node/HyperFrames, Chrome, whisper.cpp). First build is slow (Chrome +
   whisper.cpp); later builds cache.
4. Add a **Volume** mounted at `/app/projects` (Service → Settings → Volumes) so job
   data and renders survive.
5. The default start command runs `doctor` and then idles so the container stays up
   for you to shell in.

## Drive it

Open the service **Shell** in the Railway dashboard (or use the CLI):

```bash
# locally, once: npm i -g @railway/cli && railway link
railway shell            # interactive shell in the running container
# or a one-off command:
railway run bash -lc 'python3 scripts/status.py'
```

Inside, run the pipeline exactly like locally:
```bash
python3 scripts/intake.py --source /app/projects/_inbox/clip.mov --name "intro" --format long-form
python3 scripts/transcribe.py --job "intro"     # whisper.cpp (no PyTorch)
python3 scripts/rough_cut.py  --job "intro"
python3 scripts/build_graphics.py --job "intro"
python3 scripts/export.py     --job "intro" --no-downloads
```

## Getting footage in and finals out

Railway has no Finder to drag files into. Pick one:
- **Object storage (recommended):** put raw clips in an S3/R2 bucket, `curl` them into
  `/app/projects/<job>/raw/` at the start, and upload `outputs/<job>.final.mp4` back at
  the end. Cleanest for automation.
- **Volume + `railway run`:** copy files in/out through the CLI for one-offs.

## GPU

Rendering and whisper.cpp transcription run fine on CPU. Railway's GPU availability is
limited/evolving — don't assume it. If you need faster transcription, use a smaller
model (`--model tiny.en`/`base.en`); renders scale with `--workers`.

## Honest take

Railway shines for **headless, repeatable renders** (e.g. a scheduled job that
transcribes + rough-cuts a dropped clip). For the hands-on *review-and-nudge* loop —
watching `rough.mp4`, tweaking a graphic, re-rendering — running the same Docker image
**locally** (see `DOCKER.md`) is smoother, because the files are right there on your
machine. Many people do both: iterate locally, offload big batch renders to Railway.
