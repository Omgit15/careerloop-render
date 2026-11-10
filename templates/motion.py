"""Render one motion job in every requested size, with the template's locked fallback chain.

    python -m templates.motion job.json --out DIR [--template T] [--engine NAME] [--cap-s N]

The job (careerloop-studio's render-motion payload, or a template's test.json) is untrusted:
templates/rules.py validates it first, and a refused job never falls back. HTML templates must
keep every visible word inside the safe zone at all sampled times, and the data template must
show its source and date for 2 seconds or more, before any engine runs. Each engine renders
every size or the next one takes over; the chain and every failure go into DIR/motion_log.json.
--engine renders with one chain entry only (CI tests each one); --cap-s lowers the hero cap.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from templates import browser, engines, fill, rules
from templates.library import chain, library, pins


def precheck(job: dict[str, Any], page: Path, work: Path) -> None:
    """Safe zones at every size, and the source hold for data videos; Refused otherwise."""
    seconds, hold = fill.duration(job), library()["data"]["source_hold_s"]
    for size_name in job["sizes"]:
        html = fill.project(job, size_name, page, work / f"check-{size_name}") / "index.html"
        if bad := browser.outside(html, size_name, seconds):
            raise rules.Refused("text outside the safe zone: " + "; ".join(bad[:5]))
        if job["template"] == "data" and browser.shown_for(html, size_name, "#source", seconds) < hold:
            raise rules.Refused(f"source and date must stay on screen for {hold} s or more")


def attempt(job: dict[str, Any], engine: str, file: Path, out: Path, timeout: int) -> dict[str, str]:
    paths, out = {}, out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for size_name in job["sizes"]:
        path = engines.ENGINES[engine](job, size_name, file, out / f"{size_name}.mp4", timeout)
        engines.probe(path, size_name)
        paths[size_name] = path.name
    return paths


def render(job: dict[str, Any], out: Path, only: str | None = None) -> dict[str, Any]:
    started, failures = time.monotonic(), []
    entries = [e for e in chain(job["template"]) if only in (None, e[0])]
    if not entries:
        raise rules.Refused(f"{job['template']} has no engine {only!r}")
    for name, engine, file in entries:
        timeout = job["cap_s"] if engine == "blender" else library()["timeout_s"]
        work = out / "work" / name
        try:
            if file.suffix == ".html":
                precheck(job, file, work)
            sizes = attempt(job, engine, file, work, timeout)
        except rules.Refused:
            raise
        except Exception as exc:                   # an engine boundary: log it, try the next one
            failures.append({"engine": name, "error": type(exc).__name__, "detail": str(exc)[:300]})
            print(f"motion {job['id']}: {name} failed ({type(exc).__name__}); next engine", file=sys.stderr)
            continue
        for size_name, file_name in sizes.items():
            (work / file_name).replace(out / file_name)
        return {"id": job["id"], "template": job["template"], "engine": name, "sizes": sizes,
                "failures": failures, "cap_s": job["cap_s"], "render_s": round(time.monotonic() - started, 1),
                "hyperframes": pins()["npm"]["hyperframes"]["version"]}
    raise RuntimeError(f"motion {job['id']}: every engine failed: {failures}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m templates.motion")
    p.add_argument("job", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--template", help="render the same data with another template (CI)")
    p.add_argument("--engine", help="one chain entry only (CI)")
    p.add_argument("--cap-s", type=int, help="lower the hero render-time cap (CI)")
    a = p.parse_args(argv)
    raw = json.loads(a.job.read_text(encoding="utf-8"))
    job = rules.job({**raw, **({"template": a.template} if a.template else {})})
    if a.cap_s:
        job["cap_s"] = min(job["cap_s"], max(a.cap_s, 1))
    a.out.mkdir(parents=True, exist_ok=True)
    log = render(job, a.out, a.engine)
    (a.out / "motion_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(json.dumps(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
