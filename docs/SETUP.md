# Setup

Five things: Python, FFmpeg, Node 22+, the HyperFrames engine, and WhisperX. Run
`bash scripts/doctor.sh` at any point to see what's missing.

## 1. FFmpeg (video/audio muscle)

- **macOS:** `brew install ffmpeg`
- **Debian/Ubuntu:** `sudo apt-get install -y ffmpeg`
- **Windows:** `winget install Gyan.FFmpeg` (or `choco install ffmpeg`)

Verify: `ffmpeg -version` and `ffprobe -version`.

## 2. Node 22+ and the HyperFrames engine

HyperFrames renders the graphics and needs Node 22 or newer.

```bash
# nvm is the easiest way to get Node 22:
nvm install 22 && nvm use 22

# From this repo:
npm install                 # installs hyperframes (see package.json)
npm run engine:install      # npx skills add heygen-com/hyperframes --full-depth
```

`npm run engine:install` pulls the HyperFrames **agent skills** so Claude can author
compositions the engine understands. The engine version is pinned in
`skills-lock.json`; update with `npm run engine:install` again — never hand-edit
generated compositions or engine internals.

> First render will download the HyperFrames headless-Chrome renderer if it isn't
> cached. That's expected.

## 3. WhisperX (word-level transcription)

WhisperX gives us **word-level timestamps**, which is what makes precise cutting and
on-beat captions possible.

```bash
pipx install whisperx          # recommended — isolated CLI
# or, into a venv:
python3 -m venv .venv && source .venv/bin/activate && pip install whisperx
```

Notes:
- WhisperX pulls in PyTorch + faster-whisper. On Apple Silicon it runs on CPU out of
  the box; on an NVIDIA GPU it uses CUDA automatically.
- First run downloads the model (`large-v3` by default; override with
  `transcribe.py --model`). `base`/`small` are much faster if you don't need accuracy.
- Some setups need a HuggingFace token only for speaker **diarization** — we don't use
  diarization, so it's not required here.

## 4. Python

The pipeline scripts use only the standard library, so any Python 3.10+ works. For
tests: `pip install pytest` (optional — `python3 -m unittest` also works).

## 5. Assets (optional but recommended)

Drop your brand assets in `assets/` and point `config/brand.tokens.json` at them:
- `assets/fonts/` — display/caption font. The demo look uses **Coolvetica**
  (`Coolvetica.otf`). Any `.otf`/`.ttf` works.
- `assets/logos/` — `logo-mark.png`, `logo-wordmark.png`.
- `assets/mascots/` — an optional character PNG for accent graphics.
- `assets/music/` — background tracks (or reference any path at mix time).

## Check

```bash
bash scripts/doctor.sh
```
Green ✓ = ready. Yellow • = optional/nice-to-have. Red ✗ = fix before running.
