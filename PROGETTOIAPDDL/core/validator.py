import os
import subprocess
import tempfile
from typing import Dict, Any

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
    valid = (proc.returncode == 0)

    # Trova indice errore (se esiste) per riassunto
    error_idx = None
    for i, line in enumerate(full_log):
        if line.startswith("Error:") or "Expected" in line or "Got:" in line:
            error_idx = i
            break

    if not valid:
        if error_idx is not None:
            start = max(0, error_idx - 2)
            end = min(len(full_log), error_idx + 3)
            summary_lines = full_log[start:end]
        else:
            summary_lines = full_log[-5:]
        validation_summary = "\n".join(summary_lines)
    else:
        validation_summary = "✓ Sintassi valida."

    # Ricostruisco il report con le stesse chiavi della tua struttura attuale,
    # ma riempio solo valid_syntax e validation_summary
    report = {
        "valid_syntax": valid,
        "validation_summary": validation_summary,
        # Le altre chiavi esistono ma vuote/null default, perché non controlliamo semanticamente qui
        "missing_sections": [],
        "undefined_predicates_in_goal": [],
        "undefined_predicates_in_init": [],
        "undefined_objects_in_goal": [],
        "mismatched_lore_entities": [],
        "domain_mismatch": None,
        "semantic_errors": []
    }

    return report
