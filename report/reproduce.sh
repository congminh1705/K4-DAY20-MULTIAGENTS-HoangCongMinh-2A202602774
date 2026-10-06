#!/usr/bin/env bash
# Run from the repository root in Linux/WSL with the virtual environment active.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONWARNINGS=ignore
export LAB_REQUESTS_PER_SECOND=0.18
python -m pytest
python scripts/tour.py > report/tour.txt
python -m lab.runner --condition baseline --tasks learn
python -m lab.runner --condition subagents --tasks learn
python -m lab.curator
# Review generated skills without editing them; complete REPORT.md sections 1-6.
python -m lab.runner --condition skills-auto --tasks learn
mv results/skills-auto results/skills-auto-dev
echo 'Write H1-H3 in report/REPORT.md, commit hypotheses, then commit and tag freeze.'
echo 'After freeze, execute the commands in report/run-frozen.sh.'
