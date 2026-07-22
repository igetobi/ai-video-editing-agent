# AI Video Editing Agent — all dependencies baked in.
#
# One image with ffmpeg, Node 22 + HyperFrames, Chrome Headless Shell, and
# whisper.cpp (HyperFrames' light, no-PyTorch transcription engine). Run it locally
# for the interactive edit loop, or deploy it to Railway for headless rendering.
#
#   docker build -t vea .
#   docker run --rm -it -v "$PWD/projects:/app/projects" -v "$HOME/Movies:/footage" vea
#
# Build args:
#   INSTALL_WHISPER=1    build whisper.cpp (HyperFrames transcription; default on)
#   BAKE_CHROME=1        download Chrome Headless Shell into the image (default on)
#   INSTALL_WHISPERX=0   also install WhisperX (heavy: pulls in PyTorch; default off)
FROM node:22-bookworm-slim

ARG INSTALL_WHISPER=1
ARG BAKE_CHROME=1
ARG INSTALL_WHISPERX=0
# Proxy passthrough for CI/sandboxed builds (harmless when unset).
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY=""

ENV DEBIAN_FRONTEND=noninteractive \
    HYPERFRAMES_SKIP_SKILLS=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PROJECTS_DIR=/app/projects

# System deps: ffmpeg, python3, build tools for whisper.cpp, and the shared libs
# Chrome Headless Shell needs to run.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg python3 python3-pip git ca-certificates curl \
      cmake build-essential \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
      libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
      libpango-1.0-0 libcairo2 libatspi2.0-0 libxshmfence1 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Node deps (HyperFrames). Copied first for layer caching.
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

# whisper.cpp — HyperFrames' transcription engine (no PyTorch).
RUN if [ "$INSTALL_WHISPER" = "1" ]; then \
      git clone --depth 1 https://github.com/ggml-org/whisper.cpp /opt/whisper.cpp && \
      cmake -S /opt/whisper.cpp -B /opt/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release && \
      cmake --build /opt/whisper.cpp/build --config Release -j "$(nproc)" && \
      cmake --install /opt/whisper.cpp/build && \
      ( ln -sf "$(command -v whisper-cli)" /usr/local/bin/whisper-cpp || true ) && \
      ldconfig ; \
    fi

# Optional: WhisperX (heavy — PyTorch). Off by default.
RUN if [ "$INSTALL_WHISPERX" = "1" ]; then pip3 install --no-cache-dir whisperx ; fi

# App source.
COPY . .

# Bake Chrome Headless Shell so the first render is instant / offline.
RUN if [ "$BAKE_CHROME" = "1" ]; then \
      node node_modules/hyperframes/bin/hyperframes.mjs browser ensure || true ; \
    fi

# Non-fatal sanity signal at build time.
RUN node node_modules/hyperframes/bin/hyperframes.mjs doctor || true

VOLUME ["/app/projects"]

# Default to an interactive shell for the edit loop. Override on Railway with a
# specific stage command (see docs/RAILWAY.md).
CMD ["bash"]
