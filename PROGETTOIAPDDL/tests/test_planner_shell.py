"""Smoke-test the existing shell planner wrapper without requiring Fast Downward."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "planner" / "run-planner.sh"
FAKE_PLANNER = r'''
import sys
from pathlib import Path

args = sys.argv[1:]
assert "--search" in args
assert "--plan-file" in args
if any("NO_PLAN" in Path(arg).read_text(encoding="utf-8")
       for arg in args if arg.endswith("problem.pddl")):
    print("No solution")
    sys.exit(0)
path = Path(args[args.index("--plan-file") + 1])
path.write_text("(move a b)\n; cost = 1 (unit cost)\n", encoding="utf-8")
print("Solution found.")
'''


class PlannerShellTests(unittest.TestCase):
    def test_plan_is_written_only_in_session_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            work = base / "session 01"
            work.mkdir()
            (work / "domain.pddl").write_text(
                "(define (domain move-agent) (:predicates (at ?x)))", encoding="utf-8"
            )
            (work / "problem.pddl").write_text(
                "(define (problem p))", encoding="utf-8"
            )
            driver = base / "fake_downward.py"
            driver.write_text(FAKE_PLANNER, encoding="utf-8")
            env = os.environ.copy()
            env["FAST_DOWNWARD_PATH"] = str(driver)
            env["VAL_BIN"] = str(base / "missing_VAL")
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(work)],
                cwd=str(base), env=env, capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((work / "plan.txt").is_file())
            self.assertTrue((work / "plan.json").is_file())
            self.assertTrue((work / "plan.csv").is_file())
            self.assertFalse((base / "sas_plan").exists())
            self.assertFalse((base / "plan.txt").exists())

    def test_missing_plan_is_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            work = base / "session"
            work.mkdir()
            (work / "domain.pddl").write_text("(define (domain move-agent))", encoding="utf-8")
            (work / "problem.pddl").write_text("NO_PLAN", encoding="utf-8")
            driver = base / "fake_downward.py"
            driver.write_text(FAKE_PLANNER, encoding="utf-8")
            env = os.environ.copy()
            env["FAST_DOWNWARD_PATH"] = str(driver)
            env["VAL_BIN"] = str(base / "missing_VAL")
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(work)], cwd=str(base),
                env=env, capture_output=True, text=True
            )
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
