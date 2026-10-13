#!/bin/bash
# Assemble the review file incendios_fframes.mp4 (1797 frames = 59.90 s, 1080p30):
#   0.00–20.80 s  fframes render (build/ff_a.mp4)
#  20.80–53.30 s  NOT PORTED: the v10 Python frames, re-encoded, tagged «v10 Python» in the top-right corner
#  53.30–59.90 s  fframes render with the new sources/credits card (build/ff_c.mp4)
# Audio: the mastered v10 score (v10/build/music_v10.wav, −14 LUFS), padded with 0.13 s of silence to the new length,
# encoded exactly like v10/finish_v10.sh (AAC 192k 48 kHz). v10 files are only read.
set -e; cd "$(dirname "$0")/.."
FONT=media/Inter600.ttf
ffmpeg -y -v error -i build/ff_a.mp4 -i ../v10/incendios_v10.mp4 -i build/ff_c.mp4 -i ../v10/build/music_v10.wav -filter_complex \
 "[0:v]setpts=PTS-STARTPTS,format=yuv420p[a];[1:v]trim=start_frame=624:end_frame=1599,setpts=PTS-STARTPTS,drawtext=fontfile=$FONT:text='v10 Python (no portado)':x=w-tw-30:y=26:fontsize=30:fontcolor=white@0.8:box=1:boxcolor=black@0.5:boxborderw=8,format=yuv420p[b];[2:v]setpts=PTS-STARTPTS,format=yuv420p[c];[a][b][c]concat=n=3:v=1:a=0[v];[3:a]apad=whole_dur=59.9[au]" \
 -map "[v]" -map "[au]" -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p -profile:v high -r 30 -c:a aac -b:a 192k -ar 48000 -t 59.9 -movflags +faststart /tmp/incendios_fframes.mp4 && cp /tmp/incendios_fframes.mp4 incendios_fframes.mp4
ffprobe -v error -count_frames -show_entries format=duration:stream=codec_name,width,height,nb_read_frames -of default=nw=1 incendios_fframes.mp4
ffmpeg -hide_banner -nostats -i incendios_fframes.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):"
