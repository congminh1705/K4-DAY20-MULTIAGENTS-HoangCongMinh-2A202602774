"""Audit saved artifacts, table consistency and protected sources; no model calls."""
import json
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from lab.compare import build_table, load_runs
from lab.tasks import hash_skills, list_tasks

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("baseline", "subagents", "skills-auto")
FIELDS = {"task", "condition", "role", "score", "passed", "total", "checks",
          "tokens", "tool_calls", "subagent_calls", "skills_read", "skills_modified",
          "skills_sha256", "timestamp", "seconds", "final_message", "error"}


def main():
    problems = []
    paths = []
    frozen_hash = hash_skills(ROOT / "skills/auto")
    for condition in CONDITIONS:
        paths += [ROOT / "results" / condition / task.id / "run.json" for task in list_tasks()]
        for repetition in (2, 3):
            folder = ROOT / "results/bonus-6e" / f"repeat-{repetition}"
            if folder.exists():
                paths += [folder / condition / task.id / "run.json" for task in list_tasks("eval")]
    for path in paths:
        if not path.exists():
            problems.append(f"missing {path.relative_to(ROOT)}")
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if not FIELDS <= record.keys():
            problems.append(f"incomplete fields: {path.relative_to(ROOT)}")
        if not path.with_name("trace.md").exists():
            problems.append(f"missing trace: {path.relative_to(ROOT)}")
        checks = record["checks"]
        if "RateLimit" in (record.get("error") or ""):
            problems.append(f"API failure still unresolved: {path.relative_to(ROOT)}")
        if record["passed"] != sum(c["passed"] for c in checks) or record["total"] != len(checks):
            problems.append(f"inconsistent checks: {path.relative_to(ROOT)}")
        if record["total"] and abs(record["score"] - record["passed"] / record["total"]) > 1e-10:
            problems.append(f"inconsistent score: {path.relative_to(ROOT)}")
        if record["skills_modified"]:
            problems.append(f"skills modified: {path.relative_to(ROOT)}")
        if record["condition"] == "skills-auto" and record["skills_sha256"] != frozen_hash:
            problems.append(f"different frozen skill hash: {path.relative_to(ROOT)}")
    expected = build_table(load_runs(ROOT / "results"))
    bonus = ROOT / "results/bonus-6c/summary.json"
    if not bonus.exists():
        problems.append("missing bonus 6c results")
    else:
        summary = json.loads(bonus.read_text(encoding="utf-8"))
        if summary["original_bypasses"] != 3 or summary["hardened_bypasses"] != 0 or not summary["frozen_skills_unchanged"]:
            problems.append("bonus 6c results inconsistent")
    table = ROOT / "report/table.md"
    if not table.exists() or table.read_text(encoding="utf-8").strip() != expected.strip():
        problems.append("report/table.md does not match saved records")
    protected = ["tests", "tasks", "scripts", "src/lab/model.py", "src/lab/tasks.py",
                 "src/lab/grading.py", "src/lab/testing.py", "src/lab/compare.py"]
    result = subprocess.run(["git", "diff", "ad29c55", "--", *protected],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode or result.stdout:
        problems.append("protected source files differ from starter")
    secrets = [value for name, value in dotenv_values(ROOT / ".env").items()
               if name.endswith("API_KEY") and value and len(value) >= 12]
    for folder in (ROOT / "results", ROOT / "report", ROOT / "skills"):
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".md", ".txt", ".py", ".sh"}:
                content = path.read_text(encoding="utf-8")
                if any(secret in content for secret in secrets):
                    problems.append(f"API key detected in {path.relative_to(ROOT)}")
    for problem in problems:
        print("FAIL:", problem)
    print(f"Audited {len(paths)} official/bonus records: {'OK' if not problems else 'FAIL'}")
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(main())
