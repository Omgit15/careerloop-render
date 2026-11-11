# 3D (Locked Stack row 22)

The launch reel, the week's flagship, hero ad shots. 3D only where it earns its render time.

| Template | Engine | File | Use |
| --- | --- | --- | --- |
| `three` | HyperFrames with [three.js](https://threejs.org) `0.186.1` | `index.html` | default 3D |
| `hero` | headless [Blender](https://www.blender.org) `5.2.3`, Cycles on the CPU | `hero.py` | hero shots the Producer marks |
| `flat` | HyperFrames, CSS perspective layers (2.5D) | `flat.html` | the fallback for both |

- three.js is drawn only from the paused GSAP timeline, so frames are deterministic. All words are HTML inside the safe zone.
- Blender: the job's `cap_s` (careerloop-studio `lane_motion.hero.cap_s`) is the render-time cap per size, enforced as the process timeout. Over it, the chain switches to `flat`, and the log records the failure. The studio also estimates the time before dispatch and sends a `flat` job straight away when the estimate is over the cap. The title and line are fitted inside the safe zone in camera space; if they cannot fit, the render stops.
- Blender comes from the pinned download (`templates/pins.json`, SHA-256 checked); no Docker.

Job data (`test.json`): `{"title": "CareerLoop", "line": "Your next interview starts here", "frames": 24, "samples": 8}` (frames 12 to 120, samples 4 to 64).

Test renders: `python -m templates.motion templates/three/test.json --out out/three` (also with `--template hero` and `--template flat`; CI also runs `--template hero --cap-s 5` and checks that `flat` took over).
