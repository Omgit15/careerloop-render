"""Validate a render-motion payload from careerloop-studio and write the matrix for motion.yml.

    python -m templates.plan payload.json [--github-output FILE]

Payload: {"jobs": [<motion job>, ...]} (1 to library.json max_jobs). Every job goes through
templates/rules.py; any refused job fails the whole plan with its reason, so nothing half-valid
renders. Output `jobs` is the matrix: each entry is the clean job plus the tools it needs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from templates import rules
from templates.library import library


def plan(payload: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = payload.get("jobs")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= library()["max_jobs"]:
        raise rules.Refused(f"jobs: needs 1 to {library()['max_jobs']}")
    clean = [rules.job(j) for j in jobs]
    if len({j["id"] for j in clean}) != len(clean):
        raise rules.Refused("job ids must be unique")
    return [{"job": j, "tools": library()["tools"][j["template"]]} for j in clean]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m templates.plan")
    p.add_argument("payload", type=Path)
    p.add_argument("--github-output", type=Path)
    a = p.parse_args(argv)
    matrix = json.dumps(plan(json.loads(a.payload.read_text(encoding="utf-8"))), ensure_ascii=False)
    if a.github_output:
        with a.github_output.open("a", encoding="utf-8") as f:
            f.write(f"jobs={matrix}\n")
    print(matrix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
