# Explainer (Locked Stack row 20)

How tracking systems rank a resume, the six-second scan, before and after. One idea per scene, every element labelled, generic interfaces only (never a fake product screen).

- **Primary:** [ManimCE](https://pypi.org/project/manim/) `0.22.0` (`scene.py`, scene `Explainer`), written to [manim_skill](https://github.com/adithya-s-k/manim_skill)'s `manimce-best-practices`. It runs in its own venv from `requirements.txt` (exact versions, `uv pip compile --exclude-newer 2026-10-26`), with Cairo and Pango from apt. The layout is scaled into the safe zone and checked before anything animates.
- **Fallback, `hyperframes-diagram`:** `diagram.html`, the same flow as a HyperFrames diagram.

Job data (`test.json`):

```json
{"title": "How hiring software reads a resume", "steps": ["You upload your resume", "Software pulls out the text"]}
```

2 to 5 steps of at most 5 words; the title at most 8 words. Each step is 1.4 s.

Test render: `MANIM_PYTHON=.venv-manim/bin/python python -m templates.motion templates/explainer/test.json --out out/explainer`.
