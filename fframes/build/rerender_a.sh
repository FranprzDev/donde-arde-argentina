#!/bin/bash
# re-render 0–20.8 s to local disk first (the first render's mp4 on the workspace FS came out without its moov atom)
cd "$(dirname "$0")/.."; source ./setup.sh >/dev/null
S=$(date +%s)
./target/release/incendios-fframes render 0..624 -o /tmp/ff_a.mp4 > build/ff_a2.time 2>&1
E=$(date +%s); echo "wall $((E-S)) s" >> build/ff_a2.time
cp /tmp/ff_a.mp4 build/ff_a.mp4 && echo COPIED >> build/ff_a2.time
