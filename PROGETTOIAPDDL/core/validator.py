import os
import subprocess
import tempfile
from typing import Dict, Any
import re

def find_fast_downward() -> str:
    here = os.path.dirname(__file__)
    project_root = os.path.dirname(here)
    return os.path.join(project_root, "downward", "fast-downward.py")

def validate_pddl(domain: str, problem: str, lore: Any) -> Dict:
    """
    Sostituisce la validazione con Fast Downward mantenendo la stessa struttura di output.
    """
    fd = find_fast_downward()

    with tempfile.TemporaryDirectory() as tmp:
        dom_path = os.path.join(tmp, "domain.pddl")
        prob_path = os.path.join(tmp, "problem.pddl")
        with open(dom_path, "w", encoding="utf-8") as f:
            f.write(domain)
        with open(prob_path, "w", encoding="utf-8") as f:
            f.write(problem)

        cmd = [
            fd,
            "--translate", dom_path, prob_path,
            "--check-syntax"
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

    full_log = proc.stdout.splitlines()

    validation_summary_lines = []
    translate_exit_code = None

    for line in full_log:
        clean_line = line.strip(" \t\r\n->")
        # Quando trovi la linea con "translate exit code"
        if "translate exit code" in clean_line.lower():
            # Estrai il codice numerico
            match = re.search(r"translate exit code[: ]+(\d+)", clean_line, re.IGNORECASE)
            if match:
                translate_exit_code = int(match.group(1))
            break
        # Ignora righe info banali, tieni solo righe significative
        if clean_line and not clean_line.lower().startswith("info"):
            validation_summary_lines.append(clean_line)

    # Se non ha trovato "translate exit code" usa il codice di ritorno di processo
    if translate_exit_code is None:
        translate_exit_code = proc.returncode

    valid = (translate_exit_code == 0)

    validation_summary = " - ".join(validation_summary_lines) if validation_summary_lines else "✓ Sintassi valida."

    return {
        "valid_syntax": valid,
        "validation_summary": validation_summary,
        "translate_exit_code": translate_exit_code
    }

def generate_plan_with_fd(domain_str: str, problem_str: str) -> Dict:
    fd = find_fast_downward()

    with tempfile.TemporaryDirectory() as tmp:
        dom = os.path.join(tmp, "domain.pddl")
        prob = os.path.join(tmp, "problem.pddl")
        plan = os.path.join(tmp, "plan.txt")

        with open(dom, "w", encoding="utf-8") as f:
            f.write(domain_str)
        with open(prob, "w", encoding="utf-8") as f:
            f.write(problem_str)

        cmd = [
            fd,
            "--alias", "lama-first",
            "--plan-file", plan,
            dom, prob
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log = proc.stdout

        if proc.returncode == 0 and os.path.exists(plan):
            with open(plan, encoding="utf-8") as f:
                plan_txt = f.read()
            return {"found_plan": True, "plan": plan_txt, "log": log}
        else:
            return {"found_plan": False, "plan": "", "log": log}
