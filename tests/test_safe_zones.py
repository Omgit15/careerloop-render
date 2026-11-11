"""Every HTML template keeps its text inside the safe zone at all three sizes, at every sampled
time, in headless Chromium (Playwright). The data template holds its source for 2 s or more."""
import copy
import json
import urllib.request

import pytest

from templates import browser, fill, rules
from templates.library import HERE, library

SIZES = ("vertical", "square", "4x5")
PAGES = [("kinetic", "kinetic/index.html"), ("explainer", "explainer/diagram.html"),
         ("data", "data/index.html"), ("three", "three/index.html"), ("three", "three/flat.html")]


def _online() -> bool:
    try:
        with urllib.request.urlopen("https://cdn.jsdelivr.net/npm/gsap@3.14.2/package.json", timeout=10):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _online(), reason="the templates load pinned libraries from jsDelivr")


def _page(tmp_path, template: str, page: str, size_name: str, job: dict | None = None):
    raw = job or json.loads((HERE / template / "test.json").read_text(encoding="utf-8"))
    clean = rules.job(raw)
    html = fill.project(clean, size_name, HERE / page, tmp_path / f"{size_name}-{page.replace('/', '-')}")
    return clean, html / "index.html"


@pytest.mark.parametrize("size_name", SIZES)
@pytest.mark.parametrize("template, page", PAGES)
def test_text_stays_inside_the_safe_zone(tmp_path, template, page, size_name):
    job, html = _page(tmp_path, template, page, size_name)
    assert browser.outside(html, size_name, fill.duration(job)) == []


def test_a_word_too_long_for_the_safe_zone_is_caught(tmp_path):
    job = {"id": "k", "template": "kinetic", "data": {"screens": [{"text": "Supercalifragilisticexpialidocious"}]}}
    clean, html = _page(tmp_path, "kinetic", "kinetic/index.html", "vertical", job)
    assert browser.outside(html, "vertical", fill.duration(clean))


@pytest.mark.parametrize("size_name", SIZES)
def test_data_source_and_date_stay_on_screen_for_two_seconds(tmp_path, size_name):
    job, html = _page(tmp_path, "data", "data/index.html", size_name)
    assert browser.shown_for(html, size_name, "#source", fill.duration(job)) >= library()["data"]["source_hold_s"]


def test_bars_start_at_zero(tmp_path):
    raw = json.loads((HERE / "data" / "test.json").read_text(encoding="utf-8"))
    small = copy.deepcopy(raw)
    for item in small["data"]["items"]:
        item["value"] += 100 - 41                               # a top value of 100, not 41
    widths = []
    for job in (raw, small):
        _, html = _page(tmp_path, "data", "data/index.html", "square", job)
        widths.append(_bar_ratio(html))
    assert widths[0] == pytest.approx(13 / 41, abs=0.02) and widths[1] == pytest.approx(72 / 100, abs=0.02)


def _bar_ratio(html) -> float:
    """Shortest bar over longest at the end of the clip (zero-based bars keep the value ratio)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        page = browser._open(p, html, "square")
        page.evaluate(browser.SEEK, 5.0)
        w = page.evaluate("() => [...document.querySelectorAll('.bar')].map(b => b.getBoundingClientRect().width)")
    return min(w) / max(w)
