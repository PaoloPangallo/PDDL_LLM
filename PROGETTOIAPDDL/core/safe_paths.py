"""Strict, reusable checks for user-controlled session and lore names.

These identifiers are used in checkpoint filenames, generated reports, and
temporary PDDL paths. Reject traversal rather than attempting to sanitize it.
"""
from pathlib import Path
import re

_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def validate_thread_id(value: str) -> str:
    if not isinstance(value, str) or not _SESSION_ID.fullmatch(value):
        raise ValueError("Invalid thread_id: use 1-64 ASCII letters, digits, '_' or '-'")
    return value


def resolve_lore_file(lore_name: str, lore_dir: str | Path) -> Path:
    if not isinstance(lore_name, str) or not lore_name.endswith(".json"):
        raise ValueError("A .json lore filename is required")
    if lore_name != Path(lore_name).name or "\\" in lore_name:
        raise ValueError("Lore must be a filename, not a path")
    directory = Path(lore_dir).resolve()
    candidate = (directory / lore_name).resolve()
    if candidate.parent != directory or not candidate.is_file():
        raise FileNotFoundError("Lore JSON not found")
    return candidate


def retrieved_pddl_examples(records) -> list[str]:
    """Convert the DB's structured RAG hits into the PDDL text prompt expects."""
    results = []
    for record in records:
        if isinstance(record, dict):
            domain, problem = record.get("domain"), record.get("problem")
            if isinstance(domain, str) and isinstance(problem, str):
                if domain.strip() and problem.strip():
                    results.append(f"{domain.strip()}\n\n{problem.strip()}")
        elif isinstance(record, str) and record.strip():
            results.append(record.strip())
    return results
