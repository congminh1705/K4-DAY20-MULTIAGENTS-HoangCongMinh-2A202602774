"""Resume missing/API-failed runs while retaining all previous evidence and frozen skills."""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lab.runner import run_task
from lab.tasks import list_tasks

ROOT = Path(__file__).resolve().parents[1]


def resume(results):
    for condition in ("baseline", "subagents", "skills-auto"):
        for task in list_tasks():
            path = results / condition / task.id / "run.json"
            if path.exists():
                record = json.loads(path.read_text(encoding="utf-8"))
                if "RateLimit" not in (record.get("error") or ""):
                    continue
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                archive = ROOT / "results/infrastructure-errors" / condition / task.id / stamp
                shutil.copytree(path.parent, archive)
            record = run_task(task.id, condition, results_dir=results)
            print(f"{condition} {task.id}: {record['passed']}/{record['total']}; error={record['error']}", flush=True)
            if "RateLimit" in (record.get("error") or ""):
                raise RuntimeError("Quota still exhausted; stop instead of generating more failed records.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bonus-6e", action="store_true", help="Also collect 18 repeats; optional, bonus 6c is already complete.")
    args = parser.parse_args()
    resume(ROOT / "results")
    if args.bonus_6e:
        for repetition in (2, 3):
            folder = ROOT / "results/bonus-6e" / f"repeat-{repetition}"
            for condition in ("baseline", "subagents", "skills-auto"):
                for task in list_tasks("eval"):
                    path = folder / condition / task.id / "run.json"
                    if not path.exists():
                        r = run_task(task.id, condition, results_dir=folder)
                        print(f"repeat-{repetition} {condition} {task.id}: {r['passed']}/{r['total']}", flush=True)
                        if "RateLimit" in (r.get("error") or ""):
                            raise RuntimeError("Quota exhausted in bonus; stop.")
    subprocess.run([sys.executable, str(ROOT / "scripts/verify_freeze.py")], cwd=ROOT, check=True)
    for module, output in ((["-m", "lab.compare"], "table.md"),
                           ([str(ROOT / "scripts/check_breakdown.py")], "check-breakdown.txt")):
        result = subprocess.run([sys.executable, *module], cwd=ROOT, capture_output=True, text=True, check=True)
        (ROOT / "report" / output).write_text(result.stdout, encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "report/build_report.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
