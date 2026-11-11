"""Headless Chromium (Playwright) for the HTML templates: the safe-zone check that runs before
every render, and the frame-by-frame capture engine (the bang-motion export recipe: seek the
timeline, wait two animation frames, screenshot, then FFmpeg)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from templates.library import size

SEEK = "t => { for (const tl of Object.values(window.__timelines)) tl.seek(t, false); }"
PAINT = "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
# Every visible .txt element against the safe rectangle: the text's own width (a Range, so an
# overlong word that overflows its box is caught) and its line boxes' height (the element box).
OUTSIDE = """safe => [...document.querySelectorAll('.txt')].flatMap(el => {
  let o = 1;
  for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
    const s = getComputedStyle(n);
    if (s.visibility === 'hidden' || s.display === 'none') return [];
    o *= parseFloat(s.opacity);
  }
  if (o < 0.05 || !el.textContent.trim()) return [];
  const range = document.createRange(); range.selectNodeContents(el);
  const g = range.getBoundingClientRect(), b = el.getBoundingClientRect(), t = 1;
  const r = [g.left, b.top, g.right, b.bottom].map(Math.round);
  const out = r[0] < safe.left - t || r[1] < safe.top - t || r[2] > safe.right + t || r[3] > safe.bottom + t;
  return out ? [`${el.textContent.trim().slice(0, 40)} at ${r}`] : [];
})"""
VISIBLE = "sel => parseFloat(getComputedStyle(document.querySelector(sel)).opacity)"


def _open(p, html: Path, size_name: str) -> Page:
    w, h, _ = size(size_name)
    page = p.chromium.launch().new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    page.goto(html.resolve().as_uri(), wait_until="load")
    page.wait_for_function("() => !!(window.__timelines && window.__timelines.main)", timeout=60_000)
    return page


def outside(html: Path, size_name: str, seconds: float, samples: int = 24) -> list[str]:
    """Text that leaves the safe zone at any sampled time ([] when everything stays inside)."""
    w, h, s = size(size_name)
    rect = {"left": s["left"], "top": s["top"], "right": w - s["right"], "bottom": h - s["bottom"]}
    with sync_playwright() as p:
        page, found = _open(p, html, size_name), []
        for n in range(samples + 1):
            t = seconds * n / samples
            page.evaluate(SEEK, t)
            found += [f"{size_name} t={t:.2f}s: {x}" for x in page.evaluate(OUTSIDE, rect)]
    return sorted(set(found))


def shown_for(html: Path, size_name: str, selector: str, seconds: float, fps: int = 10) -> float:
    """Seconds the element is fully visible (opacity 0.99 or more), sampled at fps."""
    with sync_playwright() as p:
        page, frames = _open(p, html, size_name), 0
        for n in range(int(seconds * fps) + 1):
            page.evaluate(SEEK, n / fps)
            frames += page.evaluate(VISIBLE, selector) >= 0.99
    return frames / fps


def capture(html: Path, size_name: str, seconds: float, fps: int, out: Path, timeout: int) -> Path:
    frames = out.parent / f"{out.stem}-frames"
    frames.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        page = _open(p, html, size_name)
        for n in range(int(seconds * fps)):
            page.evaluate(SEEK, n / fps)
            page.evaluate(PAINT)
            page.screenshot(path=str(frames / f"f{n:05d}.png"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                    str(frames / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(out)], check=True, timeout=timeout)
    return out
