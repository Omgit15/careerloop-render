"""A 5-slide carousel renders to 5 JPEGs (1080x1350) whose GitHub Pages URLs map to the files."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

import render

ENGINE = os.environ.get("RENDER_ENGINE", "chromium")
JOB = {"id": "ig-test-five", "engine": ENGINE, "slides": [
    {"type": "cover", "headline": "Your resume is not read", "body": "Here is what is."},
    {"type": "body_card", "headline": "Lead with the result", "body": "Shipped work before duties."},
    {"type": "body_card", "headline": "Cut the tool list", "body": "Depth beats breadth & noise."},
    {"type": "body_card", "headline": "Match the listing", "body": "Use the words <the ad> uses."},
    {"type": "cta", "headline": "Comment SCORE", "body": "Your free Shortlist Score, in the DM."}]}


def jpeg_size(data: bytes) -> tuple[int, int]:
    """(width, height) from the JPEG start-of-frame marker."""
    i = 2
    while i + 9 < len(data):
        marker, length = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + length
    raise AssertionError("no start-of-frame marker")


def _job(tmp_path: Path, **changes) -> Path:
    path = tmp_path / "job.json"
    path.write_text(json.dumps({**JOB, **changes}), encoding="utf-8")
    return path


def test_five_slides_make_five_jpegs_with_valid_pages_urls(tmp_path):
    manifest = render.render(render.load_job(_job(tmp_path)), tmp_path, ENGINE)
    files = sorted((tmp_path / "renders" / "ig-test-five").glob("*.jpg"))
    assert [f.name for f in files] == ["01.jpg", "02.jpg", "03.jpg", "04.jpg", "05.jpg"]
    for f in files:
        data = f.read_bytes()
        assert data[:3] == b"\xff\xd8\xff" and jpeg_size(data) == (1080, 1350)
    urls = [i["url"] for i in manifest["images"]]
    assert urls == [f"https://omgit15.github.io/careerloop-render/renders/ig-test-five/{n:02d}.jpg"
                    for n in range(1, 6)]
    for url in urls:                           # the Pages path is the file's path in this repo
        u = urlsplit(url)
        assert u.scheme == "https" and u.netloc == "omgit15.github.io" and not u.query
        assert (tmp_path / u.path.removeprefix("/careerloop-render/")).is_file()
    saved = json.loads((tmp_path / "renders" / "ig-test-five" / "manifest.json").read_text())
    assert saved == manifest and manifest["count"] == 5


@pytest.mark.parametrize("bad", [{"id": "../main"}, {"id": "IG Upper"}, {"slides": JOB["slides"][:1]},
                                 {"slides": [{"type": "script", "headline": "x"}] * 2},
                                 {"engine": "firefox"}])
def test_untrusted_payload_is_refused(tmp_path, bad):
    with pytest.raises(ValueError):
        job = render.load_job(_job(tmp_path, **bad))
        render.render(job, tmp_path, job["engine"])
    assert not (tmp_path / "renders").exists()


def test_slide_text_is_html_escaped():
    ds, _ = render.design()
    inner = render.content(ds, JOB["slides"][3], 4, 5)
    assert "&lt;the ad&gt;" in inner and "<the ad>" not in inner
