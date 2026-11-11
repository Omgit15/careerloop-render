"""Validate a render-reel payload from careerloop-studio and write the matrix for reel.yml.

    python reel_plan.py payload.json [--github-output FILE]

The payload is untrusted: the studio SHA must be a full commit SHA, the runners come from an
allow-list, and every reel id must be safe as a path. Outputs: reels (the matrix as JSON),
studio_sha, first, other (the runner for the re-run) and faceless ("true" or "false").
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

CONFIG = json.loads((Path(__file__).resolve().parent / "render.json").read_text(encoding="utf-8"))["reel"]
JOB_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
SHA = re.compile(r"[0-9a-f]{40}")


def plan(payload: dict[str, Any]) -> dict[str, str]:
    sha, runners, reels = payload.get("studio_sha", ""), payload.get("runners") or [], payload.get("reels") or []
    if not SHA.fullmatch(str(sha)):
        raise ValueError("studio_sha must be a 40-character commit SHA")
    if len(runners) != 2 or any(r not in CONFIG["runners"] for r in runners) or runners[0] == runners[1]:
        raise ValueError(f"runners must be two different entries of {CONFIG['runners']}")
    if not 1 <= len(reels) <= CONFIG["max_reels"]:
        raise ValueError(f"{len(reels)} reels; need 1 to {CONFIG['max_reels']}")
    for job in reels:
        if not JOB_ID.fullmatch(str(job.get("id", ""))):
            raise ValueError("every reel id must be lowercase letters, digits and dashes")
        if not job.get("lines") or not all(isinstance(x, str) and x.strip() for x in job["lines"]):
            raise ValueError(f"{job['id']}: lines must be non-empty text")
    return {"reels": json.dumps(reels, ensure_ascii=False), "studio_sha": sha, "first": runners[0],
            "other": runners[1], "faceless": str(bool(payload.get("faceless_after_failures", True))).lower()}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python reel_plan.py")
    p.add_argument("payload", type=Path)
    p.add_argument("--github-output", type=Path)
    a = p.parse_args(argv)
    out = plan(json.loads(a.payload.read_text(encoding="utf-8")))
    lines = "".join(f"{k}={v}\n" for k, v in out.items())
    if a.github_output:
        with a.github_output.open("a", encoding="utf-8") as fh:
            fh.write(lines)
    print(lines, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
