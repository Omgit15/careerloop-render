"""The render engines. Each takes (job, size, template file, output mp4, timeout in seconds) and
returns the mp4. A timeout or a failed command raises, and motion.py moves to the next engine.
HTML templates pass the safe-zone check before any engine runs (motion.py)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from templates import browser, fill
from templates.library import HERE, library, pins, size

Engine = Callable[[dict[str, Any], str, Path, Path, int], Path]


def _run(cmd: list[str], timeout: int, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, check=True, timeout=timeout, cwd=cwd, env={**os.environ, **(env or {})})


def _job_file(job: dict[str, Any], out: Path) -> Path:
    path = out.parent / f"{out.stem}-job.json"
    path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    return path


def hyperframes(job: dict[str, Any], size_name: str, file: Path, out: Path, timeout: int) -> Path:
    """The locked install (templates/package-lock.json, `npm ci`), else npx at the pinned version."""
    work = fill.project(job, size_name, file, out.parent / f"{out.stem}-hf")
    locked = shutil.which("hyperframes", path=str(HERE / "node_modules" / ".bin"))
    cli = [locked] if locked else [shutil.which("npx") or "npx", "-y",
                                   f"hyperframes@{pins()['npm']['hyperframes']['version']}"]
    _run([*cli, "render", "--output", str(out.resolve()), "--fps", str(library()["fps"])], timeout,
         cwd=work, env={"HYPERFRAMES_SKIP_SKILLS": "1", "DO_NOT_TRACK": "1", "CI": "true"})
    return out


def frames(job: dict[str, Any], size_name: str, file: Path, out: Path, timeout: int) -> Path:
    work = fill.project(job, size_name, file, out.parent / f"{out.stem}-frames-src")
    return browser.capture(work / "index.html", size_name, fill.duration(job), library()["fps"], out, timeout)


def manim(job: dict[str, Any], size_name: str, file: Path, out: Path, timeout: int) -> Path:
    """ManimCE in the explainer venv (MANIM_PYTHON, else this interpreter)."""
    media = out.parent / f"{out.stem}-manim"
    python = os.environ.get("MANIM_PYTHON") or sys.executable
    _run([python, "-m", "manim", "render", "--format", "mp4", "--media_dir", str(media),
          "-o", out.stem, str(file), "Explainer"], timeout,
         env={"MOTION_JOB": str(_job_file(job, out)), "MOTION_SIZE": size_name})
    shutil.move(next(media.rglob(f"{out.stem}.mp4")), out)
    return out


def blender(job: dict[str, Any], size_name: str, file: Path, out: Path, timeout: int) -> Path:
    """Headless Blender, Cycles on the CPU. The timeout is the job's render-time cap."""
    shots = out.parent / f"{out.stem}-blender"
    _run([os.environ.get("BLENDER", "blender"), "-b", "--factory-startup", "-noaudio", "-P", str(file),
          "--", str(_job_file(job, out)), size_name, str(shots)], timeout)
    _run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(shots / "f%04d.png"),
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], timeout)
    return out


def bar_chart_race(job: dict[str, Any], size_name: str, file: Path, out: Path, timeout: int) -> Path:
    """dexplo/bar_chart_race in its own uv environment (it needs the older pandas/matplotlib)."""
    race = pins()["pypi"]["bar_chart_race"]
    withs = [x for dep in race["with"] for x in ("--with", dep)]
    _run(["uv", "run", "--no-project", "--python", race["python"], *withs, "python", str(file),
          str(_job_file(job, out)), str(HERE / "brand" / "tokens.json"), size_name, str(out)], timeout)
    return out


ENGINES: dict[str, Engine] = {"hyperframes": hyperframes, "frames": frames, "manim": manim,
                              "blender": blender, "bar_chart_race": bar_chart_race}


def probe(path: Path, size_name: str) -> None:
    """QC: the file exists, has video and is exactly the size's width and height."""
    w, h, _ = size(size_name)
    got = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True, timeout=60).stdout.strip()
    if got != f"{w},{h}":
        raise RuntimeError(f"{path.name}: {got or 'no video'}, expected {w},{h}")
