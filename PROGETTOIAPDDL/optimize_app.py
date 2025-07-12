# optimize_app.py

import os
import shutil
import logging
from pathlib import Path

MAX_PDDL_LENGTH = 5000
TARGET_FOLDERS_TO_CLEAN = ["llm_debug", "uploads", "tmp", "/tmp"]
TRUNCATE_EXTENSIONS = [".pddl", ".txt"]

ENV_VARS = {
    "FLASK_ENV": "production",
    "PYTHONOPTIMIZE": "2",
    "LOG_LEVEL": "WARNING"
}


def truncate_large_files(folder: str):
    for root, _, files in os.walk(folder):
        for file in files:
            if Path(file).suffix.lower() in TRUNCATE_EXTENSIONS:
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if len(content) > MAX_PDDL_LENGTH:
                        truncated = content[:MAX_PDDL_LENGTH] + "\n;; ...TRUNCATED...\n"
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(truncated)
                        print(f"✂️  File troncato: {full_path}")
                except Exception as e:
                    print(f"⚠️  Errore su {full_path}: {e}")


def clean_temp_folders():
    for folder in TARGET_FOLDERS_TO_CLEAN:
        path = Path(folder)
        if path.exists() and path.is_dir():
            try:
                shutil.rmtree(path)
                print(f"🧹 Cartella pulita: {folder}")
            except Exception as e:
                print(f"⚠️  Errore durante la pulizia di {folder}: {e}")


def set_env_vars():
    for key, value in ENV_VARS.items():
        os.environ[key] = value
        print(f"🔧 {key} = {value}")


def lower_logging_level():
    logging.getLogger().setLevel(logging.WARNING)
    print("🔕 Livello di log impostato a WARNING")


def optimize_before_launch():
    print("🚀 Ottimizzazione pre-lancio in corso...\n")
    set_env_vars()
    truncate_large_files("lore")
    truncate_large_files("uploads")
    clean_temp_folders()
    lower_logging_level()
    print("\n✅ Ottimizzazione completata.\n")
