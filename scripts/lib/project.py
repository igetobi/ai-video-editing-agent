"""Project + job model.

A "job" is one video edit. Everything for a job lives under a single directory,
``projects/<job>/``, so a job is fully self-contained, inspectable, and can be
zipped/moved without losing state. ``job.json`` is the manifest and single source
of truth for the job's format, dimensions, and per-stage status.

Layout of a job directory::

    projects/<job>/
      job.json                     # manifest (this module)
      raw/<clip>                   # original footage, never mutated
      transcript/transcript.json   # WhisperX word-level output
      transcript/corrected.json    # after caption-corrections applied
      cut/edl.json                 # the cut list (edl.py)
      cut/rough.mp4                # rendered rough cut
      graphics/plan.json           # graphics beats (plan.py)
      graphics/compositions/*.html # HyperFrames compositions per beat
      graphics/segments/*.mov      # rendered per-beat overlays (alpha)
      graphics/.render-cache.json  # incremental render cache (cache.py)
      graphics/composited.mp4      # rough cut + graphics
      captions/captions.ass        # word-level caption track
      captions/captioned.mp4       # composited + captions
      music/scored.mp4             # + background music
      thumbnail/<job>.png          # thumbnail (if generated)
      premiere/<job>.fcpxml        # Premiere off-ramp (if exported)
      outputs/<job>.final.mp4      # the shipped file
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Ordered pipeline stages. `optional` stages never block export.
STAGES: list[tuple[str, bool]] = [
    ("intake", False),
    ("rough_cut", False),
    ("graphics", False),
    ("second_pass", True),
    ("captions", True),
    ("music", True),
    ("export", False),
]

SUBDIRS = [
    "raw",
    "transcript",
    "cut",
    "graphics",
    "graphics/compositions",
    "graphics/segments",
    "captions",
    "music",
    "thumbnail",
    "premiere",
    "outputs",
]


def repo_root() -> Path:
    """Return the repository root (the folder that contains ``projects/``)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "projects").is_dir() and (parent / "scripts").is_dir():
            return parent
    # Fall back to two levels up from scripts/lib/.
    return here.parents[2]


def projects_dir() -> Path:
    return repo_root() / "projects"


def slugify(name: str) -> str:
    """Turn an arbitrary title into a filesystem-safe job slug."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "untitled"


def _now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


@dataclass
class Job:
    """In-memory view of a job. Persisted to ``<dir>/job.json``."""

    name: str
    directory: Path
    source: str = ""              # relative path (under the job dir) of the raw clip
    format: str = "long-form"     # key into config/formats.json
    fps: float = 30.0
    width: int = 1920
    height: int = 1080
    created: str = field(default_factory=_now)
    updated: str = field(default_factory=_now)
    stages: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    # ---- construction -------------------------------------------------
    @classmethod
    def create(cls, name: str, fmt: str = "long-form") -> "Job":
        slug = slugify(name)
        directory = projects_dir() / slug
        job = cls(name=slug, directory=directory, format=fmt)
        for stage, optional in STAGES:
            job.stages[stage] = {"status": "pending", "optional": optional}
        job.mkdirs()
        job.save()
        return job

    @classmethod
    def load(cls, name_or_dir: str) -> "Job":
        directory = cls._resolve_dir(name_or_dir)
        manifest = directory / "job.json"
        if not manifest.is_file():
            raise FileNotFoundError(f"No job.json found in {directory}")
        data = json.loads(manifest.read_text())
        job = cls(
            name=data["name"],
            directory=directory,
            source=data.get("source", ""),
            format=data.get("format", "long-form"),
            fps=float(data.get("fps", 30.0)),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            created=data.get("created", _now()),
            updated=data.get("updated", _now()),
            stages=data.get("stages", {}),
            meta=data.get("meta", {}),
        )
        return job

    @staticmethod
    def _resolve_dir(name_or_dir: str) -> Path:
        p = Path(name_or_dir)
        if p.is_dir():
            return p.resolve()
        return (projects_dir() / slugify(name_or_dir)).resolve()

    # ---- persistence --------------------------------------------------
    def mkdirs(self) -> None:
        for sub in SUBDIRS:
            (self.directory / sub).mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        self.updated = _now()
        self.mkdirs()
        (self.directory / "job.json").write_text(json.dumps(self.to_dict(), indent=2) + "\n")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "format": self.format,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "created": self.created,
            "updated": self.updated,
            "stages": self.stages,
            "meta": self.meta,
        }

    # ---- stage status -------------------------------------------------
    def set_stage(self, stage: str, status: str, **info: Any) -> None:
        if stage not in self.stages:
            self.stages[stage] = {}
        self.stages[stage].update({"status": status, "at": _now(), **info})
        self.save()

    def stage_status(self, stage: str) -> str:
        return self.stages.get(stage, {}).get("status", "pending")

    # ---- path helpers -------------------------------------------------
    def path(self, *parts: str) -> Path:
        return self.directory.joinpath(*parts)

    @property
    def source_path(self) -> Path:
        return self.directory / self.source if self.source else self.directory / "raw"

    @property
    def transcript_json(self) -> Path:
        return self.path("transcript", "transcript.json")

    @property
    def corrected_json(self) -> Path:
        return self.path("transcript", "corrected.json")

    @property
    def edl_json(self) -> Path:
        return self.path("cut", "edl.json")

    @property
    def rough_mp4(self) -> Path:
        return self.path("cut", "rough.mp4")

    @property
    def plan_json(self) -> Path:
        return self.path("graphics", "plan.json")

    @property
    def render_cache(self) -> Path:
        return self.path("graphics", ".render-cache.json")

    @property
    def composited_mp4(self) -> Path:
        return self.path("graphics", "composited.mp4")

    @property
    def captions_ass(self) -> Path:
        return self.path("captions", "captions.ass")

    @property
    def captioned_mp4(self) -> Path:
        return self.path("captions", "captioned.mp4")

    @property
    def scored_mp4(self) -> Path:
        return self.path("music", "scored.mp4")

    @property
    def final_mp4(self) -> Path:
        return self.path("outputs", f"{self.name}.final.mp4")

    def latest_video(self) -> Optional[Path]:
        """Return the most advanced rendered artifact that exists.

        Used by any stage that needs "the current state of the edit" as input:
        music takes captioned if present, else composited, else rough, etc.
        """
        for candidate in (
            self.scored_mp4,
            self.captioned_mp4,
            self.composited_mp4,
            self.rough_mp4,
        ):
            if candidate.is_file():
                return candidate
        return None
