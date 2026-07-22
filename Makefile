# Convenience targets. The pipeline is normally driven by Claude via the skills in
# skills/, but these let you (or CI) run stages directly.
#
#   make doctor
#   make intake SRC=~/Movies/raw.mp4 NAME="channel intro" FMT=long-form
#   make rough JOB="channel intro"
#   make graphics JOB="channel intro"
#   make captions JOB="channel intro"
#   make export JOB="channel intro"
#   make test

PY := python3
FMT ?= long-form

.PHONY: doctor intake transcribe rough graphics captions music export premiere thumb status test setup

doctor:
	bash scripts/doctor.sh

setup:
	npm install || true
	@echo "Install WhisperX + FFmpeg per docs/SETUP.md, then: make doctor"

intake:
	$(PY) scripts/intake.py --source "$(SRC)" --name "$(NAME)" --format "$(FMT)"

transcribe:
	$(PY) scripts/transcribe.py --job "$(JOB)"

rough:
	$(PY) scripts/rough_cut.py --job "$(JOB)"

graphics:
	$(PY) scripts/plan_graphics.py --job "$(JOB)" || true
	$(PY) scripts/build_graphics.py --job "$(JOB)"

captions:
	$(PY) scripts/captions.py --job "$(JOB)"

music:
	$(PY) scripts/background_music.py --job "$(JOB)" --music "$(MUSIC)"

export:
	$(PY) scripts/export.py --job "$(JOB)"

premiere:
	$(PY) scripts/to_premiere.py --job "$(JOB)"

thumb:
	$(PY) scripts/thumbnail.py --job "$(JOB)" --time $(T) --title "$(TITLE)"

status:
	$(PY) scripts/status.py $(if $(JOB),--job "$(JOB)",)

test:
	$(PY) -m pytest -q tests || $(PY) -m unittest discover -s tests -v
