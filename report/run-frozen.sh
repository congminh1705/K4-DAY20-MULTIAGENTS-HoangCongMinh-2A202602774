#!/usr/bin/env bash
# Official evaluation and bonus 6e; never regenerate skills after freeze.
# Refuse to overwrite any existing official evaluation or bonus run.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONWARNINGS=ignore
export LAB_REQUESTS_PER_SECOND=0.18
git rev-parse --verify freeze >/dev/null
for condition in baseline subagents skills-auto; do
    if test -f "results/$condition/code-eval/run.json"; then
        echo "Existing results for $condition; use a fresh results directory."
        exit 1
    fi
done
for repetition in 2 3; do
    if test -d "results/bonus-6e/repeat-$repetition"; then
        echo "Existing bonus repeat $repetition; preserve these results first."
        exit 1
    fi
done
python -m lab.runner --condition baseline --tasks eval
python -m lab.runner --condition subagents --tasks eval
python -m lab.runner --condition skills-auto --tasks all
python scripts/verify_freeze.py
python -m lab.compare > report/table.md
python scripts/check_breakdown.py > report/check-breakdown.txt
for repetition in 2 3; do
    for condition in baseline subagents skills-auto; do
        python -m lab.runner --condition "$condition" --tasks eval --results "results/bonus-6e/repeat-$repetition"
    done
done
