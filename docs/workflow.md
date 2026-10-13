# Workflow

1. **Plan** — copy `templates/video-brief.md` and fill in the hook, beats and CTA.
2. **Record** — capture gameplay on the device (e.g. `adb shell screenrecord` or the
   built-in recorder) and drop the files in `games/<slug>/raw/`.
3. **Cut** — use `scripts/make_short.sh` for vertical shorts, or edit in your
   editor of choice. Save reusable trimmed clips in `clips/`.
4. **Thumbnail** — `scripts/make_thumbnail.sh`, then save covers in `thumbnails/`.
5. **Export** — final renders go in `exports/` (not committed; upload them to the
   platform and keep a backup in cloud storage).
6. **Log** — add a row to the game's README video log.

## Specs

| Target              | Resolution | Aspect | Length       |
|---------------------|-----------|--------|--------------|
| YouTube Shorts      | 1080x1920 | 9:16   | ≤ 60 s       |
| TikTok / Reels      | 1080x1920 | 9:16   | 15–60 s      |
| Play Store preview  | 1920x1080 or 1080x1920 | 16:9 / 9:16 | 30 s–2 min |
| YouTube thumbnail   | 1280x720  | 16:9   | —            |

## Large files

Raw recordings and exports are git-ignored to keep the repo small. If you want
them versioned, enable [Git LFS](https://git-lfs.com) for `*.mp4`, `*.mov` and
`*.wav` and remove the ignore rules.
