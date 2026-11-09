"""Render one carousel job to 4:5 JPEGs with the pinned idrsdev design system (Playwright).

    python render.py job.json [--out DIR] [--engine chromium|chrome]

job.json is the careerloop-studio repository_dispatch payload:
    {"id": "ig-...", "engine": "chromium", "slides": [{"type", "headline", "body"}, ...]}
It writes DIR/renders/<id>/NN.jpg plus manifest.json with each slide's GitHub Pages URL.
The "chrome" engine is the fallback: the installed Google Chrome instead of Playwright Chromium.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "render.json").read_text(encoding="utf-8"))
JOB_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
TYPES = ("cover", "body_card", "cta")


def load_job(path: Path) -> dict[str, Any]:
    """Validate the untrusted payload: safe id (it becomes a path), slide count, slide types."""
    job = json.loads(path.read_text(encoding="utf-8"))
    if not JOB_ID.fullmatch(str(job.get("id", ""))):
        raise ValueError("job id must be lowercase letters, digits and dashes")
    slides = job.get("slides") or []
    if not CONFIG["min_slides"] <= len(slides) <= CONFIG["max_slides"]:
        raise ValueError(f"{len(slides)} slides; need {CONFIG['min_slides']} to {CONFIG['max_slides']}")
    if any(s.get("type") not in TYPES or not str(s.get("headline", "")).strip() for s in slides):
        raise ValueError(f"every slide needs a headline and a type in {TYPES}")
    return job


def design() -> tuple[dict[str, Any], dict[str, str]]:
    """The pinned design system, plus fonts.json from its download_fonts.py when present."""
    g = CONFIG["generator"]
    ds = json.loads((ROOT / g["path"] / g["design_system"]).read_text(encoding="utf-8"))
    fonts = ROOT / CONFIG["fonts"]
    return ds, json.loads(fonts.read_text(encoding="utf-8")) if fonts.is_file() else {}


def _key(family: str) -> str:
    return family.lower().replace(" ", "_")          # the keys download_fonts.py writes


def font_css(ds: dict[str, Any], fonts: dict[str, str]) -> str:
    t, key = ds["typography"], _key
    faces = [(t["font_primary"], w, f"{key(t['font_primary'])}_{k}")
             for w, k in ((400, "regular"), (600, "600"), (700, "bold"))]
    faces.append((t["font_annotation"], 700, f"{key(t['font_annotation'])}_bold"))
    return "".join(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url(data:font/woff2;"
                   f"base64,{fonts[k]}) format('woff2');}}" for fam, w, k in faces if k in fonts)


def _text(t: dict[str, Any], color: str) -> str:
    return (f"font-size:{t['size']};font-weight:{t['weight']};color:{color};"
            f"line-height:{t.get('line_height', 1.2)};letter-spacing:{t.get('letter_spacing', '0')}")


def content(ds: dict[str, Any], slide: dict[str, str], pos: int, total: int) -> str:
    """One slide's inner HTML from the design system's tokens. All text is escaped."""
    c, t, css = ds["colors"], ds["typography"]["scale"], ds["css_toolkit"]
    head, body = html.escape(slide["headline"]), html.escape(slide.get("body", ""))
    text = f'<div style="{_text(t["body"], c["slate"])};max-width:760px">{body}</div>'
    mark = f'<span style="{css["wordmark"]}">{html.escape(CONFIG["wordmark"])}</span>'
    number = f'<span style="{css["slide_number"]}">{pos:02d} / {total:02d}</span>'
    if slide["type"] == "cover":
        return (f'<div style="{_text(t["cover_headline"], c["ink"])};margin-bottom:40px">{head}</div>'
                f'{text}<div style="{css["ghost_number"]}">{total:02d}</div>{mark}'
                f'<div style="{css["swipe_hint"]}">swipe &rarr;</div>')
    if slide["type"] == "cta":
        return (f'<div style="{_text(t["cover_headline"], c["ink"])}">{head}</div>'
                f'<div style="{css["orange_rule"]}"></div>{text}{mark}{number}')
    return (f'<div style="{css["card"]}"><div style="{css["card_accent"]}"></div>'
            f'<div style="{_text(t["slide_headline"], c["ink"])};margin-bottom:24px">{head}</div>'
            f'{text}</div><div style="{css["ghost_number"]}">{pos:02d}</div>{mark}{number}')


def page(ds: dict[str, Any], fonts: dict[str, str], inner: str) -> str:
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{font_css(ds, fonts)}'
            f'*{{margin:0;padding:0;box-sizing:border-box}}body{{background:{ds["colors"]["bg"]}}}'
            f'</style></head><body><div id="s" style="{ds["css_toolkit"]["slide_base"]}">{inner}'
            "</div></body></html>")


async def shoot(docs: list[str], paths: list[Path], canvas: dict[str, str], engine: str) -> None:
    size = {"width": int(canvas["width"].removesuffix("px")),
            "height": int(canvas["height"].removesuffix("px"))}
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome" if engine == "chrome" else None)
        tab = await browser.new_page(viewport=size, device_scale_factor=1)
        for doc, path in zip(docs, paths):
            await tab.set_content(doc, wait_until="load")
            await tab.locator("#s").screenshot(path=str(path), type="jpeg",
                                               quality=CONFIG["jpeg_quality"])
        await browser.close()


def render(job: dict[str, Any], out: Path, engine: str = "chromium") -> dict[str, Any]:
    if engine not in CONFIG["engines"]:
        raise ValueError(f"engine must be one of {CONFIG['engines']}")
    ds, fonts = design()
    slides, rel = job["slides"], [CONFIG["image_path"].format(id=job["id"], n=n)
                                  for n in range(1, len(job["slides"]) + 1)]
    docs = [page(ds, fonts, content(ds, s, n, len(slides))) for n, s in enumerate(slides, 1)]
    paths = [out / r for r in rel]
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(shoot(docs, paths, ds["canvas"], engine))
    manifest = {"id": job["id"], "count": len(paths), "engine": engine,
                "images": [{"n": n, "path": r, "url": f"{CONFIG['pages_base']}/{r}"}
                           for n, r in enumerate(rel, 1)]}
    (paths[0].parent / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python render.py")
    p.add_argument("job", type=Path)
    p.add_argument("--out", type=Path, default=ROOT)
    p.add_argument("--engine", choices=CONFIG["engines"])
    a = p.parse_args(argv)
    job = load_job(a.job)
    print(json.dumps(render(job, a.out, a.engine or job.get("engine") or "chromium")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
