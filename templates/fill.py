"""Fill an HTML template for one size: brand tokens as CSS variables, the job as inert JSON, and
the pinned library URLs. Templates insert job text with textContent, never as HTML."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from templates.library import library, pins, size, tokens

SLOT = re.compile(r"__[A-Z0-9_]+__")


def duration(job: dict[str, Any]) -> float:
    t, d = library()["timing"], job["data"]
    seconds = {"kinetic": lambda: len(d["screens"]) * t["beat_s"],
               "explainer": lambda: (len(d["steps"]) + 1) * t["step_s"],
               "data": lambda: t["data_s"]}.get(job["template"], lambda: t["three_s"])()
    return round(seconds + t["tail_s"], 2)


def tokens_css(size_name: str) -> str:
    """The brand kit and the safe rectangle (#safe) for one size."""
    k, (w, h, safe) = tokens(), size(size_name)
    colours = "".join(f"--{name.replace('_', '-')}:{value};" for name, value in k["colour"].items())
    type_ = "".join(f"--{name.replace('_', '-')}:{px}px;" for name, px in k["type"].items()
                    if name != "line_height")
    font = f"'{k['font']['family']}',{k['font']['fallback']}"
    return (f":root{{{colours}{type_}--lh:{k['type']['line_height']};--font:{font};"
            f"--w-body:{k['font']['body']};--w-display:{k['font']['display']}}}"
            f"*{{margin:0;padding:0;box-sizing:border-box}}"
            f"html,body{{width:{w}px;height:{h}px;overflow:hidden;background:var(--ground)}}"
            f"#root{{position:relative;width:{w}px;height:{h}px;font-family:var(--font);"
            f"color:var(--ink);line-height:var(--lh);isolation:isolate}}"
            f"#safe{{position:absolute;top:{safe['top']}px;left:{safe['left']}px;"
            f"right:{safe['right']}px;bottom:{safe['bottom']}px}}")


def _inert(data: Any) -> str:
    """JSON that cannot close its <script> element."""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")


def page(job: dict[str, Any], size_name: str, file: Path) -> str:
    w, h, _ = size(size_name)
    npm = pins()["npm"]
    values = {"__W__": str(w), "__H__": str(h), "__DUR__": str(duration(job)),
              "__FPS__": str(library()["fps"]), "__TOKENS_CSS__": tokens_css(size_name),
              "__JOB_JSON__": _inert({**job["data"], "motion": tokens()["motion"],
                                      "timing": library()["timing"], "duration": duration(job)}),
              "__GSAP__": npm["gsap"]["url"], "__GSAP_SRI__": npm["gsap"]["sri"],
              "__D3__": npm["d3"]["url"], "__D3_SRI__": npm["d3"]["sri"], "__THREE__": npm["three"]["url"]}
    # one pass, so job text can never be re-read as a placeholder
    return SLOT.sub(lambda m: values.get(m.group(0), m.group(0)), file.read_text(encoding="utf-8"))


def project(job: dict[str, Any], size_name: str, file: Path, work: Path) -> Path:
    """A HyperFrames project directory (index.html, hyperframes.json, meta.json)."""
    work.mkdir(parents=True, exist_ok=True)
    (work / "index.html").write_text(page(job, size_name, file), encoding="utf-8")
    (work / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}), encoding="utf-8")
    (work / "meta.json").write_text(json.dumps({"id": f"{job['id']}-{size_name}",
                                                "name": job["id"]}), encoding="utf-8")
    return work
