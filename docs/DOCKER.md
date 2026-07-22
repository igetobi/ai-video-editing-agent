# Running in Docker (all deps baked in)

The fastest way to skip dependency setup entirely. One image bundles **ffmpeg**,
**Node 22 + HyperFrames**, **Chrome Headless Shell**, and **whisper.cpp** (light,
no-PyTorch transcription). Run it locally for the interactive edit loop, or deploy the
same image to Railway (see `RAILWAY.md`).

## Build

```bash
docker build -t vea .
```

Build args (all optional):

| Arg | Default | Meaning |
|-----|---------|---------|
| `INSTALL_WHISPER` | `1` | Build whisper.cpp for HyperFrames transcription (no PyTorch). |
| `BAKE_CHROME` | `1` | Download Chrome Headless Shell into the image (first render is instant). |
| `INSTALL_WHISPERX` | `0` | Also install WhisperX (heavy — pulls in PyTorch). |

Lean image (transcribe elsewhere, fetch Chrome at first run):
```bash
docker build --build-arg INSTALL_WHISPER=0 --build-arg BAKE_CHROME=0 -t vea:lean .
```

## Run — interactive (recommended)

Mount your job data, brand assets, and footage from the host so nothing is lost when
the container exits:

```bash
docker run --rm -it \
  -v "$PWD/projects:/app/projects" \
  -v "$PWD/assets:/app/assets" \
  -v "$HOME/Movies:/footage" \
  vea
```

Then, inside the container:
```bash
bash scripts/doctor.sh
python3 scripts/intake.py --source /footage/intro.mov --name "channel intro" --format long-form
python3 scripts/transcribe.py --job "channel intro"          # uses whisper.cpp by default
python3 scripts/rough_cut.py  --job "channel intro"
python3 scripts/plan_graphics.py --job "channel intro"
python3 scripts/build_graphics.py --job "channel intro"
python3 scripts/export.py     --job "channel intro"
```

Everything writes to `./projects/<job>/` on your host, so you review renders with your
normal player and re-open jobs anytime.

## Or use docker compose

```bash
FOOTAGE_DIR="$HOME/Movies" docker compose run --rm editor
```
`docker-compose.yml` wires up `projects/`, `assets/`, `/footage`, and `exports/`.

## Transcription in the container

The image ships **whisper.cpp**, so `transcribe.py` works out of the box (no
PyTorch). The first transcription downloads a small model (needs network). Pick a
model with `--model` (`tiny.en` fastest → `large-v3` most accurate). To use WhisperX
instead, build with `--build-arg INSTALL_WHISPERX=1` and run
`transcribe.py --engine whisperx`.

## GPU

CPU works for everything (transcription and rendering). If you have an NVIDIA GPU and
the NVIDIA Container Toolkit, add `--gpus all` to `docker run` — HyperFrames can use
`--gpu` for faster encodes and WhisperX will use CUDA.

## Notes

- The image does **not** contain any media or brand assets — mount those at runtime.
- Chrome needs a few hundred MB of RAM per render worker; give Docker enough memory
  (Docker Desktop → Settings → Resources) for larger renders.
