"""Explainer (Locked Stack row 20): ManimCE, written to manim_skill's manimce-best-practices.
One idea per scene, every element labelled, a generic flow (never a fake product screen).

    MOTION_JOB=job.json MOTION_SIZE=vertical python -m manim render scene.py Explainer

The layout is scaled to fit the size's safe zone and checked before anything animates."""
from __future__ import annotations

import json
import os
from pathlib import Path

from manim import (DOWN, UP, Arrow, Create, FadeIn, GrowArrow, RoundedRectangle, Scene, Text, VGroup,
                   Write, config)

LIBRARY = Path(__file__).resolve().parents[1]
TOKENS = json.loads((LIBRARY / "brand" / "tokens.json").read_text("utf-8"))
TIMING = json.loads((LIBRARY / "library.json").read_text("utf-8"))["timing"]
JOB = json.loads(Path(os.environ["MOTION_JOB"]).read_text("utf-8"))
SIZE = TOKENS["sizes"][os.environ["MOTION_SIZE"]]
(W, H), SAFE = SIZE["size"], SIZE["safe"]
C, FONT = TOKENS["colour"], TOKENS["font"]["family"]

config.pixel_width, config.pixel_height, config.frame_rate = W, H, 30
config.frame_height = 8.0
config.frame_width = 8.0 * W / H
config.background_color = C["ground"]
UNIT = config.frame_height / H                      # scene units per pixel


def safe_box() -> tuple[float, float, float, float]:
    """(left, bottom, right, top) of the safe zone in scene units."""
    half_w, half_h = config.frame_width / 2, config.frame_height / 2
    return (-half_w + SAFE["left"] * UNIT, -half_h + SAFE["bottom"] * UNIT,
            half_w - SAFE["right"] * UNIT, half_h - SAFE["top"] * UNIT)


def build() -> tuple[Text, list[VGroup], list[Arrow]]:
    """Title and step sizes keep the brand kit's title:body ratio; fit() sets the final scale."""
    body = 34
    title = Text(JOB["data"]["title"], font=FONT, weight="BOLD", color=C["ink"],
                 font_size=body * TOKENS["type"]["title"] / TOKENS["type"]["body"])
    boxes = []
    for n, step in enumerate(JOB["data"]["steps"]):
        label = Text(step, font=FONT, color=C["ink"], font_size=body)
        edge = C["accent"] if n == len(JOB["data"]["steps"]) - 1 else C["accent_2"]
        box = RoundedRectangle(corner_radius=0.12, width=label.width + 0.6, height=label.height + 0.45,
                               fill_color=C["surface"], fill_opacity=1, stroke_color=edge, stroke_width=4)
        boxes.append(VGroup(box, label))
    VGroup(*boxes).arrange(DOWN, buff=0.45)
    arrows = [Arrow(a.get_bottom(), b.get_top(), buff=0.05, color=C["muted"], stroke_width=4)
              for a, b in zip(boxes, boxes[1:])]
    return title, boxes, arrows


def fit(group: VGroup) -> None:
    """Scale the whole layout into the safe zone (with 6% slack) and centre it there; refuse if
    it still leaves the zone."""
    left, bottom, right, top = safe_box()
    scale = 0.94 * min((right - left) / group.width, (top - bottom) / group.height, 1.0)
    group.scale(scale).move_to([(left + right) / 2, (bottom + top) / 2, 0])
    if (group.get_left()[0] < left or group.get_right()[0] > right or group.get_bottom()[1] < bottom
            or group.get_top()[1] > top):
        raise ValueError("explainer text leaves the safe zone")


class Explainer(Scene):
    def construct(self) -> None:
        title, boxes, arrows = build()
        flow = VGroup(*boxes, *arrows)
        fit(VGroup(title, flow).arrange(DOWN, buff=0.6))
        step = TIMING["step_s"]
        self.play(Write(title), run_time=min(1.0, step))
        for n, box in enumerate(boxes):
            if n:
                self.play(GrowArrow(arrows[n - 1]), run_time=0.3)
            self.play(Create(box[0]), FadeIn(box[1], shift=UP * 0.1), run_time=step - 0.3)
        self.wait(TIMING["tail_s"])
