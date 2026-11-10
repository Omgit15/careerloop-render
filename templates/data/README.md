# Data video (Locked Stack row 21)

News and data desk, hiring numbers, Verified Jobs Drop counts. Only Anvesh's sourced numbers.

- **Primary, `hyperframes-d3`:** HyperFrames with a D3 template (`index.html`): `d3.scaleLinear` with domain `[0, max]`, so bars always start at zero.
- **Fallback:** [bar_chart_race](https://github.com/dexplo/bar_chart_race) `0.1.0` (`race.py`), in its own uv environment (Python 3.11, pandas 1.5.3, matplotlib 3.7.5), bars growing from zero.

The rules are code (`templates/rules.py`), and a refused job never falls back:

- every number needs a `source` and a `date` (`YYYY-MM` or `YYYY-MM-DD`, not in the future);
- values are numbers of zero or more; a share (`unit` `%`, `percent` or `share`) needs `sample_size` of 10 or more, shown on screen;
- no salary figures: a title, unit or label with a salary word or currency (`library.json` `data.salary_terms`) is refused;
- the source and date stay on screen for 2 seconds or more (checked in Chromium before rendering).

Job data (`test.json`, sample numbers for the test render only):

```json
{"title": "Where freshers found their first job", "unit": "%", "sample_size": 1200,
 "items": [{"label": "Job portals", "value": 41, "source": "Sample survey (test data)", "date": "2026-10"}]}
```

Test render: `python -m templates.motion templates/data/test.json --out out/data`.
