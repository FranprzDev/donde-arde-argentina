#!/usr/bin/env bash
# YouTube thumbnail (1280x720 JPG) from a real frame of the video: the map on the right, the title on the left.
#
# A thumbnail cut from the video itself shows exactly what the viewer gets (no generated imagery) and reuses the
# video's typography. Steps: grab one frame with ffmpeg, crop the map area, darken/stretch it, multiply a radial
# vignette so its edges melt into black, place it on a black canvas and draw the title lines with ImageMagick.
#
# Usage: scripts/make_thumbnail.sh VIDEO.mp4 OUT.jpg [options]
#
# Frame and map:
#   --time T            frame time in seconds (default 15)
#   --crop WxH+X+Y      crop of the source frame (default 640x1080+960+0, the map half of a 1920x1080 frame)
#   --level LO,HI       ImageMagick -level for the map (default 10%,58%)
#   --map-at +X+Y       where the map goes on the 1280x720 canvas (default +790+0)
#   --vignette LO,HI    -level of the radial vignette mask; raise LO to darken the edges (default 22%,100%)
# Title (up to three lines, each with its own colour; an empty line is skipped):
#   --line1 TEXT --color1 C   (default «¿DÓNDE», white)
#   --line2 TEXT --color2 C   (default «ARDE», #FF8A1F)
#   --line3 TEXT --color3 C   (default «ARGENTINA?», white)
#   --title-size PT          (default 150)
# Subtitle (two lines):
#   --sub1 TEXT --sub1-color C   (default «26,6 MILLONES DE HA QUEMADAS», #FFB347)
#   --sub2 TEXT --sub2-color C   (default «2012–2025 · DATOS SATELITALES», #BBBBBB)
#   --sub-size PT                (default 44)
# Fonts:
#   --font FILE         default <repo>/fonts/BebasNeue-Regular.ttf
#   --quality Q         JPEG quality (default 92)
#
# Requirements: ffmpeg, ImageMagick 7 (`magick`) or 6 (`convert`).
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

VIDEO=${1:?usage: make_thumbnail.sh VIDEO.mp4 OUT.jpg [options]}
OUT=${2:?usage: make_thumbnail.sh VIDEO.mp4 OUT.jpg [options]}
shift 2

TIME=15
CROP=640x1080+960+0
LEVEL=10%,58%
MAP_AT=+790+0
LINE1='¿DÓNDE';     COLOR1='#FFFFFF'
LINE2='ARDE';       COLOR2='#FF8A1F'
LINE3='ARGENTINA?'; COLOR3='#FFFFFF'
TITLE_SIZE=150
SUB1='26,6 MILLONES DE HA QUEMADAS';  SUB1_COLOR='#FFB347'
SUB2='2012–2025 · DATOS SATELITALES'; SUB2_COLOR='#BBBBBB'
SUB_SIZE=44
FONT=$REPO/fonts/BebasNeue-Regular.ttf
QUALITY=92
VIGNETTE=22%,100%

while [ $# -gt 0 ]; do
  case $1 in
    --time) TIME=$2 ;;
    --crop) CROP=$2 ;;
    --level) LEVEL=$2 ;;
    --map-at) MAP_AT=$2 ;;
    --line1) LINE1=$2 ;;
    --line2) LINE2=$2 ;;
    --line3) LINE3=$2 ;;
    --color1) COLOR1=$2 ;;
    --color2) COLOR2=$2 ;;
    --color3) COLOR3=$2 ;;
    --title-size) TITLE_SIZE=$2 ;;
    --sub1) SUB1=$2 ;;
    --sub2) SUB2=$2 ;;
    --sub1-color) SUB1_COLOR=$2 ;;
    --sub2-color) SUB2_COLOR=$2 ;;
    --sub-size) SUB_SIZE=$2 ;;
    --font) FONT=$2 ;;
    --quality) QUALITY=$2 ;;
    --vignette) VIGNETTE=$2 ;;
    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift 2
done

[ -s "$VIDEO" ] || { echo "video not found: $VIDEO" >&2; exit 2; }
[ -s "$FONT" ] || { echo "font not found: $FONT" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH" >&2; exit 2; }
if command -v magick >/dev/null; then IM=(magick); ID=(magick identify)
elif command -v convert >/dev/null; then IM=(convert); ID=(identify); else
  echo "ImageMagick not found" >&2; exit 2; fi

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# 1) the frame, scaled to 1920x1080 so the crop geometry holds for any master size
ffmpeg -y -v error -ss "$TIME" -i "$VIDEO" -frames:v 1 -vf scale=1920:1080 "$TMP/frame.png"

# 2) map: crop, fit to the canvas height, darken/stretch, radial vignette multiplied in
"${IM[@]}" "$TMP/frame.png" -crop "$CROP" +repage -resize x720 -level "$LEVEL" "$TMP/map.png"
MW=$("${ID[@]}" -format '%w' "$TMP/map.png"); MH=$("${ID[@]}" -format '%h' "$TMP/map.png")
# elliptical: a square gradient stretched to the map's aspect, cut to black a little before its edge
"${IM[@]}" -size 1000x1000 radial-gradient:white-black -level "$VIGNETTE" -resize "${MW}x${MH}!" "$TMP/vignette.png"
"${IM[@]}" "$TMP/map.png" "$TMP/vignette.png" -compose multiply -composite "$TMP/map_v.png"

# 3) canvas + map + text (line tops at fixed offsets from the title size, left margin 56 px)
LH=$(( TITLE_SIZE * 95 / 100 ))   # line pitch of the title
Y1=$(( 360 - LH * 3 / 2 - SUB_SIZE * 3 / 2 ))
args=(-size 1280x720 xc:black "$TMP/map_v.png" -geometry "$MAP_AT" -compose over -composite -font "$FONT" -gravity northwest)
y=$Y1
for i in 1 2 3; do
  eval "t=\$LINE$i; c=\$COLOR$i"
  if [ -n "$t" ]; then args+=(-fill "$c" -pointsize "$TITLE_SIZE" -annotate "+56+$y" "$t"); fi
  y=$(( y + LH ))
done
y=$(( y + SUB_SIZE * 3 / 4 ))
[ -n "$SUB1" ] && args+=(-fill "$SUB1_COLOR" -pointsize "$SUB_SIZE" -annotate "+58+$y" "$SUB1")
y=$(( y + SUB_SIZE * 120 / 100 ))
[ -n "$SUB2" ] && args+=(-fill "$SUB2_COLOR" -pointsize "$SUB_SIZE" -annotate "+58+$y" "$SUB2")

mkdir -p "$(dirname "$OUT")"
"${IM[@]}" "${args[@]}" -strip -quality "$QUALITY" "$OUT"
echo "thumbnail: $OUT ($("${ID[@]}" -format '%wx%h' "$OUT"))"
