#!/bin/bash
# times the v10 Python renderer on the same frame ranges (2 workers, like build_v10.sh)
cd "$(dirname "$0")/.."
source ../v10/env.sh
python3 prep/time_python.py 0 624 2 > build/py_a.time 2>&1
python3 prep/time_python.py 1599 1793 2 > build/py_c.time 2>&1
echo PY_DONE >> build/py_c.time
