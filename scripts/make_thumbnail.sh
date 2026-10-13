#!/usr/bin/env bash
# Grab a single frame from a video as a PNG thumbnail.
# Usage: scripts/make_thumbnail.sh <input> <output.png> [timestamp=00:00:01]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <input> <output.png> [timestamp]" >&2
  exit 1
fi

mkdir -p "$(dirname "$2")"
ffmpeg -hide_banner -y -ss "${3:-00:00:01}" -i "$1" -frames:v 1 "$2"
echo "Wrote $2"
