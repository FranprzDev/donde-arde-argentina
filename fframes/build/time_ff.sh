#!/bin/bash
# times fframes renders of the ported ranges (wall + CPU), output to build/
cd "$(dirname "$0")/.."
source ./setup.sh >/dev/null
for r in "0..624 a" "1599..1797 c"; do set -- $r
  S=$(date +%s.%N); { time ./target/release/incendios-fframes render $1 -o build/ff_$2.mp4 ; } 2> build/ff_$2.time
  E=$(date +%s.%N); echo "range $1 wall $(echo "$E - $S" | bc)" >> build/ff_$2.time
done
echo FF_DONE >> build/ff_c.time
