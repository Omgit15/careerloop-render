"""reel_plan.py turns a render-reel payload into the matrix and refuses unsafe input."""
import json

import pytest

import reel_plan

SHA = "a" * 40
JOB = {"id": "reel-20261110-six-seconds", "lang": "en", "lines": ["Your resume gets six seconds."]}
GOOD = {"studio_sha": SHA, "runners": ["ubuntu-24.04", "ubuntu-22.04"],
        "faceless_after_failures": True, "reels": [JOB]}


def test_plan_writes_the_matrix_and_the_two_runners(tmp_path):
    out = reel_plan.plan(GOOD)
    assert json.loads(out["reels"]) == [JOB]
    assert (out["first"], out["other"], out["faceless"], out["studio_sha"]) == \
        ("ubuntu-24.04", "ubuntu-22.04", "true", SHA)
    payload, gh = tmp_path / "p.json", tmp_path / "out"
    payload.write_text(json.dumps(GOOD), encoding="utf-8")
    assert reel_plan.main([str(payload), "--github-output", str(gh)]) == 0
    assert "other=ubuntu-22.04" in gh.read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", [
    {"studio_sha": "main"},
    {"runners": ["ubuntu-24.04", "ubuntu-24.04"]},
    {"runners": ["self-hosted", "ubuntu-22.04"]},
    {"reels": []},
    {"reels": [{**JOB, "id": "../escape"}]},
    {"reels": [{**JOB, "lines": []}]},
])
def test_plan_refuses_unsafe_payloads(bad):
    with pytest.raises(ValueError):
        reel_plan.plan({**GOOD, **bad})
