"""Run Fast Downward in an isolated temporary working directory.

FAST_DOWNWARD_PATH points to the downloaded `fast-downward.py` driver.
The validator checks translation, not whether a plan exists.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def find_fast_downward() -> str:
    configured = os.getenv("FAST_DOWNWARD_PATH")
    candidates = ([Path(configured).expanduser()] if configured else [
        PROJECT_ROOT / "downward" / "fast-downward.py",
        PROJECT_ROOT.parent / "downward" / "fast-downward.py",
    ])
    for path in candidates:
        if path.is_file():
            return str(path.resolve())
    raise FileNotFoundError(
        "Fast Downward not found: set FAST_DOWNWARD_PATH to fast-downward.py"
    )


def _run(args: list[str], cwd: str, timeout: int):
    """Invoke the Python driver explicitly, independent of executable bits."""
    return subprocess.run(
        [sys.executable, find_fast_downward(), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def validate_pddl(domain: str, problem: str, lore: Any = None) -> Dict:
    """Return original result keys for compatibility with both LangGraph pipelines.

    `valid_syntax` means the Fast Downward translator accepted the task.
    This is not a formal guarantee that lore semantics or goal intent are met.
    """
    if not isinstance(domain, str) or not isinstance(problem, str):
        raise TypeError("PDDL domain and problem must be strings")
    with tempfile.TemporaryDirectory(prefix="pddl_validation_") as tmp:
        dom = Path(tmp) / "domain.pddl"
        prob = Path(tmp) / "problem.pddl"
        dom.write_text(domain, encoding="utf-8")
        prob.write_text(problem, encoding="utf-8")
        try:
            # Official Fast Downward translator command; no unsupported --check-syntax.
            proc = _run(["--translate", str(dom), str(prob)], cwd=tmp, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "valid_syntax": False,
                "validation_summary": f"Fast Downward could not validate: {exc}",
                "translate_exit_code": 124 if isinstance(exc, subprocess.TimeoutExpired) else 127,
            }
    combined_log = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
    return {
        "valid_syntax": proc.returncode == 0,
        "validation_summary": combined_log[-4000:] if combined_log else (
            "Translation succeeded." if proc.returncode == 0 else "Translation failed."
        ),
        "translate_exit_code": proc.returncode,
    }


def generate_plan_with_fd(domain_str: str, problem_str: str) -> Dict:
    """Find a plan with Fast Downward, isolating outputs from concurrent runs."""
    with tempfile.TemporaryDirectory(prefix="pddl_plan_") as tmp:
        dom = Path(tmp) / "domain.pddl"
        prob = Path(tmp) / "problem.pddl"
        plan = Path(tmp) / "plan.txt"
        dom.write_text(domain_str, encoding="utf-8")
        prob.write_text(problem_str, encoding="utf-8")
        try:
            proc = _run(
                ["--alias", "seq-sat-lama-2011", "--plan-file", str(plan),
                 str(dom), str(prob)],
                cwd=tmp, timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"found_plan": False, "plan": "", "log": f"Fast Downward failed: {exc}"}
        combined_log = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
        if proc.returncode == 0 and plan.is_file():
            return {
                "found_plan": True, "plan": plan.read_text(encoding="utf-8"),
                "log": combined_log,
            }
        return {"found_plan": False, "plan": "", "log": combined_log}
