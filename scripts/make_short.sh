#!/usr/bin/env bash
# Cut a clip from a recording and render it as a 1080x1920 vertical short
# (YouTube Shorts / TikTok / Reels / store preview).
# Usage: scripts/make_short.sh <input> <output.mp4> [start=00:00:00] [duration=30]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <input> <output.mp4> [start] [duration-seconds]" >&2
  exit 1
fi

input="$1"
output="$2"
start="${3:-00:00:00}"
duration="${4:-30}"

mkdir -p "$(dirname "$output")"

# Scale to cover 1080x1920, then center-crop. Works for both portrait
# and landscape recordings.
ffmpeg -hide_banner -y -ss "$start" -t "$duration" -i "$input" \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 160k -ar 48000 \
  -movflags +faststart \
  "$output"

echo "Wrote $output"
