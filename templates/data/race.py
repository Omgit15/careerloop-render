"""Data video fallback (Locked Stack row 21): dexplo/bar_chart_race, run in its own uv environment
(engines.bar_chart_race). Bars grow from zero to each sourced value; the source, date and sample
size stay on screen for the whole clip. The job was validated by templates/rules.py first.

    python race.py job.json tokens.json vertical out.mp4"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bar_chart_race as bcr
import matplotlib.pyplot as plt
import pandas as pd

DPI = 120


def source_line(d: dict) -> str:
    sources = "; ".join(dict.fromkeys(f"{i['source']}, {i['date']}" for i in d["items"]))
    share = d["unit"].lower() in ("%", "percent", "share")
    return f"Source: {sources}" + (f" · n = {d['sample_size']:,}" if share else "")


def main(job_file: str, tokens_file: str, size_name: str, out: str) -> None:
    job, tokens = json.loads(Path(job_file).read_text("utf-8")), json.loads(Path(tokens_file).read_text("utf-8"))
    d, c, s = job["data"], tokens["colour"], tokens["sizes"][size_name]
    (w, h), safe = s["size"], s["safe"]
    labels = [i["label"] for i in d["items"]]
    frame = pd.DataFrame([[0.0] * len(labels), [float(i["value"]) for i in d["items"]]],
                         columns=labels, index=[0, 1])
    plt.rcParams.update({"font.family": tokens["font"]["family"], "text.color": c["ink"],
                         "axes.labelcolor": c["ink"], "xtick.color": c["muted"], "ytick.color": c["ink"]})
    fig = plt.figure(figsize=(w / DPI, h / DPI), dpi=DPI, facecolor=c["ground"])
    left = (safe["left"] + 0.3 * (w - safe["left"] - safe["right"])) / w      # room for the labels
    bottom, top = (safe["bottom"] + 90) / h, 1 - (safe["top"] + 140) / h        # source and title
    ax = fig.add_axes([left, bottom, 1 - safe["right"] / w - left - 0.08, top - bottom], facecolor=c["ground"])
    fig.text(safe["left"] / w, 1 - (safe["top"] + 60) / h, d["title"], fontsize=30, weight="bold",
             color=c["ink"], va="center")
    fig.text(safe["left"] / w, (safe["bottom"] + 30) / h, source_line(d), fontsize=14, color=c["muted"],
             va="center")
    bcr.bar_chart_race(df=frame, filename=out, orientation="h", sort="desc", n_bars=len(labels), fig=fig,
                       cmap=[c["accent"], c["accent_2"]], period_label=False, steps_per_period=60,
                       period_length=3000, bar_label_size=16, tick_label_size=16,
                       filter_column_colors=False, fixed_max=True, dpi=DPI)


if __name__ == "__main__":
    main(*sys.argv[1:5])
