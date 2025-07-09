#!/usr/bin/env python3
# validator.py
# Sostituisce la validazione interna con Fast Downward
# Mantiene la stessa signature: validate_pddl(domain: str, problem: str, lore: dict) -> dict

import os
import subprocess
import tempfile
import sys
from typing import Dict

def find_fast_downward() -> str:
    """Restituisce il path a fast-downward.py, relativo a questo file."""
    here = os.path.dirname(__file__)            # .../PROGETTOIAPDDL/game
    project_root = os.path.dirname(here)        # .../PROGETTOIAPDDL
    return os.path.join(project_root, "external", "downward", "fast-downward.py")

def validate_pddl(domain: str, problem: str, lore: dict) -> Dict:
    """
    Valida domain/problem usando Fast Downward:
      --translate ... --check-syntax

    Ritorna un report dict con:
      - 'valid_syntax': bool
      - 'validation_summary': stringa con stdout+stderr di Fast Downward
    """
    fd = find_fast_downward()

    # Scriviamo i contenuti passati a disco in file temporanei
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
    valid   = (proc.returncode == 0)

    # Se c'è un errore, cerchiamo l'indice della prima riga significativa
    if not valid:
        error_idx = None
        for i, line in enumerate(full_log):
            if line.startswith("Error:") or "Expected" in line or "Got:" in line:
                error_idx = i
                break

        if error_idx is not None:
            # prendi un paio di righe di contesto attorno all'errore
            start = max(0, error_idx - 2)
            end   = min(len(full_log), error_idx + 3)
            summary_lines = full_log[start:end]
        else:
            # fallback: ultime 5 righe se non trovi "Error:" o simili
            summary_lines = full_log[-5:]
        summary = "\n".join(summary_lines)
    else:
        summary = "✓ Sintassi valida."

    return {
        "valid_syntax": valid,
        "validation_summary": summary
    }

def generate_plan_with_fd(domain_str: str, problem_str: str) -> Dict:
    """
    Invoca Fast Downward per cercare un piano.
    Ritorna un dict con:
      - 'found_plan': bool
      - 'plan': str  (testo del piano, o empty se non trovato)
      - 'log': str   (stdout completo di FD)
    """
    fd = find_fast_downward()  # stessa funzione che già usi

    with tempfile.TemporaryDirectory() as tmp:
        dom = os.path.join(tmp, "domain.pddl")
        prob = os.path.join(tmp, "problem.pddl")
        plan = os.path.join(tmp, "plan.txt")

        with open(dom, "w", encoding="utf-8") as f: f.write(domain_str)
        with open(prob, "w", encoding="utf-8") as f: f.write(problem_str)

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

# Se eseguito da riga di comando, esempio di summary JSON
if __name__ == "__main__":
    import json
    # Carica i file di test usati finora
    with open("uploads/lore-generated/domain.pddl", "r", encoding="utf-8") as f:
        domain_content = f.read()
    with open("uploads/lore-generated/problem.pddl", "r", encoding="utf-8") as f:
        problem_content = f.read()
    with open("lore/example_lore.json", "r", encoding="utf-8") as f:
        lore_data = json.load(f)

    report = validate_pddl(domain_content, problem_content, lore_data)
    print(json.dumps(report, indent=2, ensure_ascii=False))
