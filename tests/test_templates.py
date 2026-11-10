"""Motion templates: the data rule, job validation, filling, and the fallback chain (mocked
engines). Real renders run in the templates workflow (HyperFrames, Manim, Blender, FFmpeg)."""
import copy
import json
import subprocess
from pathlib import Path

import pytest

from templates import engines, fill, motion, rules
from templates.library import HERE, chain, size

DATA = json.loads((HERE / "data" / "test.json").read_text(encoding="utf-8"))
THREE = json.loads((HERE / "three" / "test.json").read_text(encoding="utf-8"))


def _data(**item_changes) -> dict:
    job = copy.deepcopy(DATA)
    job["data"]["items"][0].update(item_changes)
    return job


def test_every_template_has_a_readme_and_a_valid_test_file():
    for name in ("kinetic", "explainer", "data", "three"):
        assert (HERE / name / "README.md").is_file()
        job = rules.job(json.loads((HERE / name / "test.json").read_text(encoding="utf-8")))
        assert job["sizes"] == ["vertical", "square", "4x5"]


@pytest.mark.parametrize("change, reason", [
    ({"source": ""}, "no source"), ({"date": ""}, "no date"), ({"date": "last year"}, "no date"),
    ({"date": "2999-01"}, "future"), ({"value": -3}, "zero or more"), ({"value": "41"}, "number")])
def test_data_template_refuses_a_number_without_source_or_date(change, reason):
    with pytest.raises(rules.Refused, match=reason):
        rules.job(_data(**change))
    item = {k: v for k, v in DATA["data"]["items"][0].items() if k not in change}
    with pytest.raises(rules.Refused):
        rules.job({**DATA, "data": {**DATA["data"], "items": [item, *DATA["data"]["items"][1:]]}})


@pytest.mark.parametrize("label", ["Average salary", "Fresher CTC", "12 LPA offers", "Pay in ₹"])
def test_data_template_refuses_salary_figures(label):
    with pytest.raises(rules.Refused, match="salary"):
        rules.job(_data(label=label))


def test_a_share_needs_a_sample_of_ten_or_more():
    job = copy.deepcopy(DATA)
    job["data"]["sample_size"] = 9
    with pytest.raises(rules.Refused, match="sample size"):
        rules.job(job)
    assert rules.job(DATA)["data"]["sample_size"] == 1200


def test_kinetic_keeps_six_words_on_screen_and_unsafe_ids_are_refused():
    seven = {"id": "k", "template": "kinetic", "data": {"screens": [{"text": "one two three four five six seven"}]}}
    with pytest.raises(rules.Refused, match="at most 6"):
        rules.job(seven)
    with pytest.raises(rules.Refused, match="id"):
        rules.job({**DATA, "id": "../main"})


def test_job_text_is_inert_in_the_page(tmp_path):
    job = rules.job(_data(label="</script><b>x</b> __W__"))
    html = fill.page(job, "square", HERE / "data" / "index.html")
    inert = html.split('id="job" type="application/json">')[1].split("</script>")[0]
    assert "<b>" not in html and "__W__" in inert          # not closed early, not re-filled
    assert 'data-width="1080" data-height="1080"' in html and "top:65px" in html


def test_three_sizes_and_safe_zones_come_from_the_tokens():
    assert [size(s)[:2] for s in ("vertical", "square", "4x5")] == [(1080, 1920), (1080, 1080), (1080, 1350)]


def _fake(log: list, fail: set):
    def engine(job, size_name, file, out, timeout):
        log.append((file.name, size_name, timeout))
        if file.name in fail:
            raise subprocess.TimeoutExpired("blender", timeout)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"mp4")
        return out
    return engine


def _mocked(monkeypatch, fail: set) -> list:
    log = []
    for name in engines.ENGINES:
        monkeypatch.setitem(engines.ENGINES, name, _fake(log, fail))
    monkeypatch.setattr(engines, "probe", lambda path, size_name: None)
    monkeypatch.setattr(motion, "precheck", lambda job, page, work: None)
    return log


def test_blender_over_the_cap_switches_to_2_5d(monkeypatch, tmp_path):
    log = _mocked(monkeypatch, fail={"hero.py"})
    job = rules.job({**THREE, "template": "hero", "cap_s": 30})
    got = motion.render(job, tmp_path)
    assert got["engine"] == "flat" and got["failures"][0]["error"] == "TimeoutExpired"
    assert log[0] == ("hero.py", "vertical", 30)                 # the cap is Blender's timeout
    assert sorted(p.name for p in tmp_path.glob("*.mp4")) == ["4x5.mp4", "square.mp4", "vertical.mp4"]


def test_a_refused_job_never_falls_back(monkeypatch, tmp_path):
    _mocked(monkeypatch, fail=set())

    def outside(job, page, work):
        raise rules.Refused("text outside the safe zone")
    monkeypatch.setattr(motion, "precheck", outside)
    with pytest.raises(rules.Refused):
        motion.render(rules.job(DATA), tmp_path)


def test_every_chain_ends_in_a_locked_fallback():
    names = {t: [n for n, _, _ in chain(t)] for t in ("kinetic", "explainer", "data", "three", "hero")}
    assert names == {"kinetic": ["hyperframes", "bang-motion"], "explainer": ["manim", "hyperframes-diagram"],
                     "data": ["hyperframes-d3", "bar_chart_race"], "three": ["three", "flat"],
                     "hero": ["blender", "flat"]}
    assert all(f.is_file() for t in names for _, _, f in chain(t))
