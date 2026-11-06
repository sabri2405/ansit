# Ansit (أنصِت)

Daily Quran clips for Instagram `@ansit.quran`, built and posted by GitHub Actions. Repo: `sabri2405/ansit`, production branch `main`.

## Rules
- Never type Quranic text by hand. Verse text, timings and translations come from the APIs in `daily.py`.
- Never post, approve or re-run publishing without the owner's approval. Every post is public.
- Never commit `.env`. Never print its values; secrets live in GitHub Actions Secrets.
- Never quote hadith or attribute a saying to the Prophet ﷺ without a verified source and grading.
- Background clips must show no people. Check any new clip before adding it.
- Edit clips with Remotion (`video/src`). ffmpeg only prepares audio and frames.

## Flow
`daily.yml` is scheduled hourly from 09:07 to 14:07 Mecca because GitHub delays and drops scheduled runs; its `gate` job lets one through each day. `daily.py build` renders the next item in `content/queue.json`, the clip goes to a GitHub release and to the Telegram bot, the `instagram` environment waits for approval, then it posts at 20:00 Mecca (allowed 13:00 to 22:00).

A commit changing `content/run-now.txt` on `main` starts a run. `content/telegram-test.txt` tests Telegram.

## Files
- `content/queue.json`: passages, scenes per ayah, text look (`stroke`, `edges`, `plate`), `en` for English
- `content/backgrounds.json`: clip library by theme
- `content/captions.json`: rotating duas and hashtags, five tags per post
- `content/state.json`: next queue position, advanced after each post

## Local run
`cd video && npm ci`, then `python daily.py build --still 300` for one frame or `python daily.py build` for the clip.

## Open work
Telegram approval instead of GitHub, TikTok posting (needs TikTok app approval), podcast clips (rights and Instagram reuse rules apply).

## Compact instructions
Keep open work, the last error and its cause, and any decision the owner made. Drop tool output and clip review details.
