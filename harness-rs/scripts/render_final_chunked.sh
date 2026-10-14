#!/usr/bin/env bash
# Final (1080p) render in small, retried, resumable chunks for memory-limited machines.
#
# Why: fframes decodes every raster a frame references, and a full 1080p render of a heavy story can be OOM-killed
# when the machine's RAM is shared with other jobs. This script renders short frame ranges, each in its own process,
# with only the assets that range needs, retries a killed chunk, skips chunks that already finished (so a rerun
# resumes), joins the parts without re-encoding, muxes the score once and runs `qa --final` on the result.
#
# Usage:
#   scripts/render_final_chunked.sh -n FRAMES -o OUT.mp4 [options]
#
# Options (every option also has an environment variable; flags win):
#   -s, --story DIR        story folder (STORY_DIR, default stories/incendios-argentina)
#   -b, --bin PATH         story binary (STORY_BIN, default $CARGO_TARGET_DIR/release/incendios)
#   -n, --frames N         total frame count (FRAMES, required)
#   -f, --fps N            frames per second, used for the mux length (FPS, default 30)
#   -t, --step N           frames per chunk (STEP, default 37)
#       --tail-from N      from this frame on use --tail-step instead (TAIL_FROM, default: off)
#       --tail-step N      chunk size after --tail-from, for the heaviest stretch (TAIL_STEP, default 6)
#   -r, --retries N        attempts per chunk (RETRIES, default 8)
#       --sleep S          seconds to wait between attempts (RETRY_SLEEP, default 20)
#   -w, --work DIR         chunk folder (WORK_DIR, default <story>/build/chunks1080)
#   -a, --audio FILE       score to mux (AUDIO, default <story>/build/assets/score.wav)
#       --prefix NAME      environment prefix the story binary reads (ENV_PREFIX, default INCENDIOS):
#                          <prefix>_PROBE, <prefix>_ASSETS, <prefix>_NO_AUDIO, <prefix>_PASSTHROUGH
#       --no-qa            skip the final `qa --final` (NO_QA=1)
#   -o, --out FILE         output MP4 (OUT, required)
#
# Example (fires story, 59.5 s at 30 fps, smaller chunks for the timelapse tail):
#   source env.sh && cargo build --release
#   scripts/render_final_chunked.sh -n 1785 --tail-from 1332 --tail-step 6 -o /tmp/final_1080p.mp4
#
# Requirements: the story's release binary, the story's assets already built (`<bin> assets`, `<bin> music`), ffmpeg.
# Keep the chunk folder on the same filesystem as the assets: they are hard-linked (copied otherwise, slower).
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

STORY_DIR=${STORY_DIR:-$HERE/stories/incendios-argentina}
STORY_BIN=${STORY_BIN:-${CARGO_TARGET_DIR:-$HERE/target}/release/incendios}
FRAMES=${FRAMES:-}
FPS=${FPS:-30}
STEP=${STEP:-37}
TAIL_FROM=${TAIL_FROM:-}
TAIL_STEP=${TAIL_STEP:-6}
RETRIES=${RETRIES:-8}
RETRY_SLEEP=${RETRY_SLEEP:-20}
WORK_DIR=${WORK_DIR:-}
AUDIO=${AUDIO:-}
ENV_PREFIX=${ENV_PREFIX:-INCENDIOS}
NO_QA=${NO_QA:-}
OUT=${OUT:-}

usage() { sed -n '2,33p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case $1 in
    -s|--story) STORY_DIR=$2; shift 2 ;;
    -b|--bin) STORY_BIN=$2; shift 2 ;;
    -n|--frames) FRAMES=$2; shift 2 ;;
    -f|--fps) FPS=$2; shift 2 ;;
    -t|--step) STEP=$2; shift 2 ;;
    --tail-from) TAIL_FROM=$2; shift 2 ;;
    --tail-step) TAIL_STEP=$2; shift 2 ;;
    -r|--retries) RETRIES=$2; shift 2 ;;
    --sleep) RETRY_SLEEP=$2; shift 2 ;;
    -w|--work) WORK_DIR=$2; shift 2 ;;
    -a|--audio) AUDIO=$2; shift 2 ;;
    --prefix) ENV_PREFIX=$2; shift 2 ;;
    --no-qa) NO_QA=1; shift ;;
    -o|--out) OUT=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$FRAMES" ] || { echo "missing --frames" >&2; exit 2; }
[ -n "$OUT" ] || { echo "missing --out" >&2; exit 2; }
[ -x "$STORY_BIN" ] || { echo "story binary not found: $STORY_BIN (cargo build --release)" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH" >&2; exit 2; }

STORY_DIR=$(cd "$STORY_DIR" && pwd)
SRC=$STORY_DIR/build/assets
WORK_DIR=${WORK_DIR:-$STORY_DIR/build/chunks1080}
AUDIO=${AUDIO:-$SRC/score.wav}
[ -d "$SRC" ] || { echo "assets not built: $SRC" >&2; exit 2; }
[ -s "$AUDIO" ] || { echo "score not found: $AUDIO" >&2; exit 2; }
mkdir -p "$WORK_DIR" "$(dirname "$OUT")"
WORK_DIR=$(cd "$WORK_DIR" && pwd)
OUT=$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")
AUDIO=$(cd "$(dirname "$AUDIO")" && pwd)/$(basename "$AUDIO")
STORY_BIN=$(cd "$(dirname "$STORY_BIN")" && pwd)/$(basename "$STORY_BIN")

PROBE_VAR=${ENV_PREFIX}_PROBE
ASSETS_VAR=${ENV_PREFIX}_ASSETS
NO_AUDIO_VAR=${ENV_PREFIX}_NO_AUDIO
PASS_VAR=${ENV_PREFIX}_PASSTHROUGH

# run the story binary with the chunk environment: assets folder first, then the binary's own args
run_bin() {
  local assets=$1; shift
  env "$ASSETS_VAR=$assets" "$NO_AUDIO_VAR=1" "$PASS_VAR=1" "$STORY_BIN" "$@"
}

PARTS=$WORK_DIR/parts.txt
: > "$PARTS"
EMPTY=$WORK_DIR/empty
mkdir -p "$EMPTY"

# the story binary resolves story.toml and build/ from its own manifest dir or STORY; run from the story folder
cd "$STORY_DIR"

a=0
while [ "$a" -lt "$FRAMES" ]; do
  s=$STEP
  if [ -n "$TAIL_FROM" ] && [ "$a" -ge "$TAIL_FROM" ]; then s=$TAIL_STEP; fi
  b=$((a + s)); [ "$b" -gt "$FRAMES" ] && b=$FRAMES
  part=$WORK_DIR/part_$(printf %05d "$a").mp4

  if [ -s "$part" ]; then
    echo "chunk $a..$b: done, skipping"
  else
    # 1) probe: record every asset href of the range without drawing, at a tiny scale, with an empty asset folder
    probe=$WORK_DIR/probe_$a.txt
    rm -f "$probe"
    if ! env "$PROBE_VAR=$probe" "$ASSETS_VAR=$EMPTY" "$NO_AUDIO_VAR=1" "$PASS_VAR=1" \
        "$STORY_BIN" render "${a}f..${b}f" --scale 0.125 -o "$WORK_DIR/probe.mp4" >"$WORK_DIR/probe_$a.log" 2>&1; then
      echo "probe failed for chunk $a..$b (see $WORK_DIR/probe_$a.log)" >&2; exit 1
    fi

    # 2) hard-link only those assets into a per-chunk folder
    D=$WORK_DIR/assets_$a
    rm -rf "$D"; mkdir -p "$D"
    if [ -f "$probe" ]; then
      sort -u "$probe" | while IFS= read -r u; do
        [ -n "$u" ] || continue
        mkdir -p "$D/$(dirname "$u")"
        ln -f "$SRC/$u" "$D/$u" 2>/dev/null || cp "$SRC/$u" "$D/$u"
      done
    fi

    # 3) render at full scale, retrying when the process is killed
    ok=
    for ((t = 1; t <= RETRIES; t++)); do
      if run_bin "$D" render "${a}f..${b}f" --scale 1 -o "$part" >"$WORK_DIR/part_$a.log" 2>&1 && [ -s "$part" ]; then
        ok=1; break
      fi
      echo "chunk $a..$b: attempt $t/$RETRIES failed, retrying in ${RETRY_SLEEP}s" >&2
      rm -f "$part"; sleep "$RETRY_SLEEP"
    done
    rm -rf "$D"
    [ -n "$ok" ] || { echo "chunk $a..$b failed after $RETRIES attempts (see $WORK_DIR/part_$a.log)" >&2; exit 1; }
    echo "chunk $a..$b: rendered"
  fi
  echo "file '$part'" >> "$PARTS"
  a=$b
done
rm -f "$WORK_DIR/probe.mp4"

# 4) join the parts without re-encoding and mux the score once
DUR=$(awk -v n="$FRAMES" -v f="$FPS" 'BEGIN { printf "%.3f", n / f }')
ffmpeg -y -v error -f concat -safe 0 -i "$PARTS" -i "$AUDIO" -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 256k -t "$DUR" -movflags +faststart "$OUT"
echo "muxed: $OUT ($DUR s)"

# 5) QA against the final resolution
if [ -z "$NO_QA" ]; then
  "$STORY_BIN" qa "$OUT" --final
fi
