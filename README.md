# Game Videos — Scorpion Labs

Promo, gameplay and store-preview videos for Scorpion Labs Android games.

## Layout

```
games/<game-slug>/
  raw/          unedited recordings (git-ignored)
  clips/        trimmed source clips
  audio/        music and SFX
  thumbnails/   covers and screenshots
  exports/      final renders (git-ignored)
scripts/        ffmpeg helpers
templates/      video brief and per-game README templates
docs/           workflow notes
```

## Quick start

Requires `ffmpeg`.

```bash
# Add a new game
scripts/new_game.sh my-game "My Game"

# Cut a 30 s vertical short starting at 0:12
scripts/make_short.sh games/flap-king-infinity/raw/session1.mp4 \
  games/flap-king-infinity/exports/short-01.mp4 00:00:12 30

# Grab a thumbnail frame
scripts/make_thumbnail.sh games/flap-king-infinity/exports/short-01.mp4 \
  games/flap-king-infinity/thumbnails/short-01.png 00:00:05
```

See [docs/workflow.md](docs/workflow.md) for the full process.

## Games

- [Flap King Infinity](games/flap-king-infinity/)
