#!/bin/bash
# concat chunks + mux the mastered score -> /tmp first (faststart), then copy into the workspace; verify with ffprobe + ebur128.
# v5/v6: the score is limited to -2.8 dBTP in music_v7.py (CEIL_DB) because the AAC encode overshoots ~0.8 dB; this script FAILS
#     if the muxed file's true peak is above -1.5 dBFS (fix: rerun music_v7.py with a lower CEIL_DB, e.g. CEIL_DB=-3.3).
set -e; cd "$(dirname "$0")"; source ./env.sh
DUR=$(python3 -c "import render_v7 as R; print(R.TOTAL)")
ls build/c_*.mp4 | grep -v tmp | sort | sed "s/^build\//file '/; s/$/'/" > build/list.txt
ffmpeg -y -v error -f concat -safe 0 -i build/list.txt -c copy build/video_only.mp4
ffmpeg -y -v error -i build/video_only.mp4 -i build/music_v7.wav -map 0:v -map 1:a \
  -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p -profile:v high -r 30 \
  -c:a aac -b:a 192k -ar 48000 -t $DUR -movflags +faststart /tmp/incendios_v7.mp4
ffprobe -v error -show_entries format=duration,size:stream=codec_name,profile,width,height,r_frame_rate,sample_rate,nb_frames -of default=nw=1 /tmp/incendios_v7.mp4
M=$(ffmpeg -hide_banner -nostats -i /tmp/incendios_v7.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):")
echo "$M"
PK=$(echo "$M" | awk '/Peak:/{print $2}')
python3 -c "import sys; pk=float('$PK'); sys.exit(0 if pk <= -1.5 else 1)" || { echo "TRUE PEAK $PK dBFS > -1.5: lower CEIL_DB and rerun music_v7.py"; exit 1; }
cp /tmp/incendios_v7.mp4 incendios_v7.mp4
echo FINISH_DONE
