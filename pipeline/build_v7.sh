#!/bin/bash
# all frame chunks (2 parallel workers, 60-frame chunks; skips chunks already built) -> finish_v7.sh
# run detached:  setsid nohup bash build_v7.sh > build.log 2>&1 &
set -e
cd "$(dirname "$0")"
source ./env.sh
mkdir -p build
N=$(python3 -c "import render_v7 as R; print(round(R.TOTAL*30))")
[ -f build/music_v7.wav ] || python3 music_v7.py
work() { for f in $(seq 0 60 $((N-1))); do if [ $(( (f/60) % 2 )) -eq $1 ]; then c=$(printf "build/c_%05d.mp4" $f); [ -f $c ] || python3 chunk_v7.py $f $(( f+60 < N ? f+60 : N )); fi; done; }
work 0 & work 1 &
wait
bash finish_v7.sh
echo BUILD_DONE
