# Kinetic type (Locked Stack row 19)

Hooks, myth and fact, checklists, ad openers. One screen per beat, at most 6 words on a screen, the key word in the brand accent.

- **Primary:** [HyperFrames](https://github.com/heygen-com/hyperframes) `0.8.200` (`npx hyperframes render`), built to the Sunwood [motion-reel skill](https://github.com/Sunwood-ai-labs/hyperframes-motion-reel-skill) (beat grid, GSAP on a paused timeline) and [motionmaxxing](https://github.com/Tejashmakwana/motionmaxxing)'s craft laws (land decelerates, leave accelerates, almost nothing fades between scenes).
- **Fallback 1, `bang-motion`:** the same seekable page captured frame by frame in headless Chromium and encoded with FFmpeg, the export recipe of [bang-motion](https://github.com/bangtutorial/bang-motion) (`references/architecture.md`: seek, two animation frames, screenshot). It needs no HyperFrames.
- **Fallback 2, [opus-video-skills](https://github.com/tuzhechen2005/opus-video-skills) `kinetic-reel`:** a canvas renderer with its own page contract (`window.renderAt`), so it is a manual rebuild by the Motion Designer, not an automatic engine.

Job data (`test.json`):

```json
{"screens": [{"text": "Six seconds.", "key": "Six"}, {"text": "That is the whole first scan.", "key": "scan"}]}
```

Each screen is 1.6 s (`library.json` `timing.beat_s`). Text is checked against the safe zone of every size before rendering.

Test render: `python -m templates.motion templates/kinetic/test.json --out out/kinetic` (CI job `templates`).
