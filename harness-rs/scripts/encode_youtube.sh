#!/usr/bin/env bash
# Upload-ready re-encode of a final master for YouTube (or any platform that re-encodes on ingest).
#
# The chunked master is joined without re-encoding, so it keeps the render's high bitrate (the fires story: 95 MB for
# 59.5 s). x264 at CRF 20 brings it to ~40 % of the size (38 MB) with no visible loss, uploads faster and is less
# likely to fail in a browser upload. The audio is copied untouched, so the mastered loudness is kept.
#
# Usage: scripts/encode_youtube.sh IN.mp4 [OUT.mp4]
#   OUT defaults to IN with a _youtube suffix.
# Environment: CRF (default 20), PRESET (default slow), SKIP_QA=1 to skip the ffprobe summary.
set -euo pipefail

IN=${1:?usage: encode_youtube.sh IN.mp4 [OUT.mp4]}
OUT=${2:-${IN%.*}_youtube.mp4}
CRF=${CRF:-20}
PRESET=${PRESET:-slow}

[ -s "$IN" ] || { echo "input not found: $IN" >&2; exit 2; }
[ "$IN" != "$OUT" ] || { echo "output must differ from input" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH" >&2; exit 2; }

ffmpeg -y -v error -i "$IN" -map 0:v:0 -map 0:a? \
  -c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p \
  -c:a copy -movflags +faststart "$OUT"

if [ -z "${SKIP_QA:-}" ] && command -v ffprobe >/dev/null; then
  for f in "$IN" "$OUT"; do
    size=$(du -h "$f" | cut -f1)
    info=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,pix_fmt:format=duration \
      -of default=noprint_wrappers=1:nokey=1 "$f" | paste -sd' ' -)
    echo "$f: $size ($info)"
  done
fi
