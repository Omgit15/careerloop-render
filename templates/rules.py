"""Validate one untrusted motion job before anything renders. Refused jobs never fall back.

Data rule (Motion Designer sheet): every number needs a source and a date, a share needs a sample
of 10 or more, values are zero or more (bars start at zero), and no salary figure is ever shown.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from templates.library import library, tokens

DATE = re.compile(r"\d{4}-\d{2}(-\d{2})?")


class Refused(ValueError):
    """The job breaks a library rule; it is sent back, not rendered with a fallback."""


def _text(value: Any, what: str, words: int | None = None) -> str:
    text = " ".join(str(value or "").split())
    if not text or len(text) > library()["limits"]["text_chars"]:
        raise Refused(f"{what}: needs 1 to {library()['limits']['text_chars']} characters")
    if words and len(text.split()) > words:
        raise Refused(f"{what}: {len(text.split())} words, at most {words}")
    return text


def _count(items: list[Any], key: str, what: str) -> list[Any]:
    lo, hi = library()["limits"][key]
    if not isinstance(items, list) or not lo <= len(items) <= hi:
        raise Refused(f"{what}: needs {lo} to {hi}")
    return items


def salary(text: str) -> bool:
    terms, low = library()["data"]["salary_terms"], text.lower()
    words = set(re.findall(r"[a-z]+", low))
    return any(t in words if t.isalpha() else t in low for t in terms)


def _date(value: Any, what: str) -> str:
    text = str(value or "").strip()
    if not DATE.fullmatch(text):
        raise Refused(f"{what}: no date (YYYY-MM or YYYY-MM-DD)")
    if text[:7] > dt.date.today().isoformat()[:7]:
        raise Refused(f"{what}: date {text} is in the future")
    return text


def _item(item: dict[str, Any], share: bool, n: int) -> dict[str, Any]:
    what = f"number {n}"
    label = _text(item.get("label"), f"{what} label")
    value = item.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise Refused(f"{what}: value must be a number of zero or more (bars start at zero)")
    if share and value > 100:
        raise Refused(f"{what}: a share above 100")
    return {"label": label[:library()["limits"]["label_chars"]], "value": value,
            "source": _text(item.get("source"), f"{what}: no source"), "date": _date(item.get("date"), what)}


def data(d: dict[str, Any]) -> dict[str, Any]:
    rules = library()["data"]
    title, unit = _text(d.get("title"), "title", library()["limits"]["title_words"]), str(d.get("unit", ""))
    share = unit.strip().lower() in rules["share_units"]
    items = [_item(i, share, n) for n, i in enumerate(_count(d.get("items"), "items", "numbers"), 1)]
    shown = " ".join([title, unit, *(i["label"] for i in items)])
    if salary(shown):
        raise Refused("no salary figures in a data video")
    sample = d.get("sample_size")
    if share and (not isinstance(sample, int) or sample < rules["min_sample"]):
        raise Refused(f"a share needs a sample size of {rules['min_sample']} or more")
    return {"title": title, "unit": unit.strip()[:12], "items": items, "sample_size": sample}


def kinetic(d: dict[str, Any]) -> dict[str, Any]:
    most, screens = library()["limits"]["words_on_screen"], []
    for n, s in enumerate(_count(d.get("screens"), "screens", "screens"), 1):
        text = _text(s.get("text"), f"screen {n}", most)
        key = str(s.get("key", "")).strip()
        screens.append({"text": text, "key": key if key and key in text else ""})
    return {"screens": screens}


def explainer(d: dict[str, Any]) -> dict[str, Any]:
    lim = library()["limits"]
    steps = [_text(s, f"step {n}", lim["step_words"])
             for n, s in enumerate(_count(d.get("steps"), "steps", "steps"), 1)]
    return {"title": _text(d.get("title"), "title", lim["title_words"]), "steps": steps}


def three(d: dict[str, Any]) -> dict[str, Any]:
    lim, hero = library()["limits"], library()["hero"]
    out = {"title": _text(d.get("title"), "title", lim["title_words"]),
           "line": _text(d["line"], "line", lim["title_words"]) if d.get("line") else ""}
    for key, default in (("frames", 48), ("samples", 16)):
        lo, hi = hero[key]
        out[key] = min(max(int(d.get(key, default)), lo), hi)
    return out


DATA = {"kinetic": kinetic, "explainer": explainer, "data": data, "three": three, "hero": three,
        "flat": three}


def job(raw: dict[str, Any]) -> dict[str, Any]:
    """A clean copy of the job, or Refused with the reason."""
    if not re.fullmatch(library()["id"], str(raw.get("id", ""))):
        raise Refused("id must be lowercase letters, digits and dashes (it becomes a path)")
    template = raw.get("template")
    if template not in DATA:
        raise Refused(f"template must be one of {sorted(DATA)}")
    sizes = raw.get("sizes") or list(tokens()["sizes"])
    if not set(sizes) <= set(tokens()["sizes"]) or len(set(sizes)) != len(sizes):
        raise Refused(f"sizes must come from {list(tokens()['sizes'])}")
    lo, hi = library()["hero"]["cap_s"]
    cap = min(max(int(raw.get("cap_s", 600)), lo), hi)
    return {"id": raw["id"], "template": template, "sizes": sizes, "cap_s": cap,
            "data": DATA[template](raw.get("data") or {})}
