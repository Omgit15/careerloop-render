# careerloop-render

Public render repo for CareerLoop (Locked Stack rows 12 and 29). It turns an Instagram carousel job into 1080x1350 JPEGs and serves them from GitHub Pages, so the Instagram Content Publishing API can fetch each `image_url`.

## How it works

1. careerloop-studio's Instagram lane (`lanes/instagram/carousel.py`) sends `repository_dispatch` with event `render-carousel` and RENDER_REPO_TOKEN. Payload:
   `{"id": "ig-20261110-topic", "engine": "chromium", "slides": [{"type": "cover|body_card|cta", "headline": "...", "body": "..."}]}`
2. `.github/workflows/render.yml` checks out the pinned [idrsdev/instagram-carousel-generator](https://github.com/idrsdev/instagram-carousel-generator) (SHA in `render.json`, never copied in), downloads its fonts, and runs `render.py`. The design-system tokens come from the pinned generator; Playwright screenshots each slide as a JPEG.
3. The JPEGs and a `manifest.json` are committed to `renders/<id>/` on `main`. Pages (legacy build, branch `main`, folder `/`) serves them at `https://omgit15.github.io/careerloop-render/renders/<id>/NN.jpg`.

`render.py` validates the untrusted payload: the id must be lowercase letters, digits and dashes (it becomes a path), 2 to 10 slides, known slide types, and all text is HTML-escaped.

Fallback (Locked Stack row 12): `"engine": "chrome"` renders with the runner's installed Google Chrome instead of Playwright's Chromium. The output stays JPEG, because Instagram accepts only JPEG.

## Reels (Locked Stack row 29, CPU matrix)

1. careerloop-studio's video lane (`lanes/video/render.py`) sends `repository_dispatch` with event `render-reel`:
   `{"studio_sha": "<40-hex>", "runners": ["ubuntu-24.04", "ubuntu-22.04"], "faceless_after_failures": true, "reels": [<job>, ...]}`
2. `.github/workflows/reel.yml`: `reel_plan.py` validates the untrusted payload (full commit SHA, runner allow-list from `render.json`, path-safe ids, 1 to 20 reels) and builds the matrix. Job `first` renders every reel on the first runner. Job `retry` re-runs each reel that is not on `main` yet, once, on the other runner; if that second try fails too, the faceless version ships (`--faceless`, unless the studio switched `faceless_after_failures` off).
3. Each render is the composite action `.github/actions/reel`: it checks out careerloop-studio at `studio_sha` with the read-only `STUDIO_READ_TOKEN`, installs FFmpeg (libass), `fonts-noto-core`, uv and the studio's pinned requirements, runs `python -m lanes.video build`, and commits `renders/<id>/reel.mp4` and `reel_log.json` to `main`. Pages serves `https://omgit15.github.io/careerloop-render/renders/<id>/reel.mp4`, the `video_url` the studio queued.

Secrets (names only): `STUDIO_READ_TOKEN` (fine-grained, careerloop-studio Contents read-only) and `PEXELS_API_KEY` (free Pexels key for MoneyPrinterTurbo and short-video-maker stock footage; without it the reel ships on the plain brand background). The studio code, its pinned adopted repos and its config run here; nothing is copied in.

## Commands

```
python -m uv venv --python 3.12 .venv
python -m uv pip install --python .venv -r requirements.txt
git clone https://github.com/idrsdev/instagram-carousel-generator vendor/idrs
git -C vendor/idrs checkout 44e6ee5979864a21fd9e47425fcd6fa8242bfe99
python -m playwright install chromium        # or RENDER_ENGINE=chrome to use installed Chrome
python vendor/idrs/skills/social-carousel-generator/scripts/download_fonts.py \
  --ds vendor/idrs/skills/social-carousel-generator/references/design-system.sample.json --out fonts.json
python -m pytest -q                          # test: 5 slides -> 5 JPEGs; reel payload validation
python reel_plan.py payload.json             # the reel matrix for one payload, by hand
python render.py job.json --out .            # one render by hand
```

Health: the `test` workflow on every pull request. Pins: `render.json` (generator SHA), `requirements.txt` (exact versions, `uv pip compile --exclude-newer 2026-10-26`), and every action by commit SHA.

## Rollback

Revert the PR's merge commit (reels: removing `reel.yml` stops new reel renders; the studio keeps dispatching and its queued reels wait with a founder alert at publish time). A bad render is removed by deleting `renders/<id>/` on `main`; publishing that item then fails with a founder alert and it stays queued until it is rendered again (run `render.yml` by hand with the job JSON).
