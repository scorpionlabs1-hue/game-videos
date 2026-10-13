#!/usr/bin/env bash
# Scaffold the folder layout for a new game.
# Usage: scripts/new_game.sh <game-slug> ["Display Name"]
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <game-slug> [\"Display Name\"]" >&2
  exit 1
fi

slug="$1"
name="${2:-$1}"
root="$(cd "$(dirname "$0")/.." && pwd)"
dir="$root/games/$slug"

if [[ -e "$dir" ]]; then
  echo "games/$slug already exists" >&2
  exit 1
fi

for sub in raw clips audio thumbnails exports; do
  mkdir -p "$dir/$sub"
  touch "$dir/$sub/.gitkeep"
done

sed "s/{{GAME_NAME}}/$name/g" "$root/templates/game-readme.md" > "$dir/README.md"
echo "Created games/$slug"
