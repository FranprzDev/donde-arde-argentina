#!/usr/bin/env bash
# Download one Google Drive file (a raw clip or a motion asset) for the promo template.
#
# Files up to 100 MB come down in one request with the `gws` CLI. Larger files are fetched in 90 MB byte ranges in
# parallel (the Drive API caps a single media response at 100 MiB) and joined. An existing non-empty OUT is kept, so
# reruns are cheap. `promo fetch CONFIG` calls this for every shot with a `drive_id` whose file is missing.
#
# Usage:
#   scripts/drive_download.sh FILE_ID OUT [SIZE_BYTES]
#   scripts/drive_download.sh --list LIST.txt DIR     # LIST: "FILE_ID NAME" per line -> DIR/NAME
#
# Auth: `gws` uses its own login. The ranged path calls the Drive REST API with curl; set DRIVE_TOKEN to an OAuth
# access token (sent as a Bearer header), or run where an identity gateway injects it.
# Environment: STEP (range size, default 90000000), FORCE=1 to re-download.
set -euo pipefail

STEP=${STEP:-90000000}
API=https://www.googleapis.com/drive/v3/files

usage() { sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

fetch_one() {
  local id=$1 out=$2 size=${3:-}
  if [ -s "$out" ] && [ -z "${FORCE:-}" ]; then echo "$out: present"; return 0; fi
  mkdir -p "$(dirname "$out")"
  if [ -z "$size" ] && command -v gws >/dev/null; then
    size=$(gws drive files get --params "{\"fileId\":\"$id\",\"fields\":\"size\"}" 2>/dev/null | sed -n 's/.*"size": *"\{0,1\}\([0-9]*\).*/\1/p' | head -1)
  fi
  local auth=()
  [ -n "${DRIVE_TOKEN:-}" ] && auth=(-H "Authorization: Bearer $DRIVE_TOKEN")
  if [ -n "$size" ] && [ "$size" -gt 100000000 ]; then
    local parts=() i=0 s e
    for ((s = 0; s < size; s += STEP)); do
      e=$((s + STEP - 1)); parts+=("$out.part$i")
      curl -sf "${auth[@]}" -r "$s-$e" -o "$out.part$i" "$API/$id?alt=media" &
      i=$((i + 1))
    done
    wait
    cat "${parts[@]}" > "$out.tmp" && rm -f "${parts[@]}"
    mv "$out.tmp" "$out"
  elif command -v gws >/dev/null; then
    gws drive files get --params "{\"fileId\":\"$id\",\"alt\":\"media\"}" --output "$out.tmp" >/dev/null
    mv "$out.tmp" "$out"
  else
    curl -sf "${auth[@]}" -o "$out.tmp" "$API/$id?alt=media" && mv "$out.tmp" "$out"
  fi
  local got; got=$(stat -c %s "$out")
  if [ -n "$size" ] && [ "$got" != "$size" ]; then echo "$out: got $got of $size bytes" >&2; rm -f "$out"; return 1; fi
  echo "$out: $got bytes"
}

case ${1:-} in
  -h|--help|"") usage; [ -n "${1:-}" ]; exit $? ;;
  --list)
    LIST=${2:?usage: drive_download.sh --list LIST.txt DIR}; DIR=${3:?usage: drive_download.sh --list LIST.txt DIR}
    fail=0
    while read -r id name _; do
      [ -z "$id" ] || [ "${id:0:1}" = "#" ] && continue
      fetch_one "$id" "$DIR/$name" || fail=1
    done < "$LIST"
    exit $fail ;;
  *) fetch_one "$1" "${2:?usage: drive_download.sh FILE_ID OUT [SIZE_BYTES]}" "${3:-}" ;;
esac
