#!/bin/sh
# Week 8: every sweep in the order it was run. Thinking off for all (Week 7's headline setting).
cd "$(dirname "$0")/.." || exit 1
run() { echo "=== $1 x$2 ==="; .venv/bin/python week8_trajectory_eval.py run --variant "$1" --repeats "$2" --workers 4 2>&1 | grep -v '^$'; }
run before 3
run after 3
run defended 3
run attack 2
run attack_defended 2
run attack_subtle 2            # written after attack 1 got 0/20
run attack_subtle_defended 2
echo DONE
