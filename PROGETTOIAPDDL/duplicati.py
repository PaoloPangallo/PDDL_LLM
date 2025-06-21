import os
import re
from collections import defaultdict

PROJECT_DIR = "."  # o "game/" se vuoi limitarlo

def find_function_defs(base_path):
    pattern = re.compile(r"^\s*def\s+(\w+)\s*\(", re.MULTILINE)
    function_map = defaultdict(list)

    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        for func_name in matches:
                            function_map[func_name].append(full_path)
                except Exception as e:
                    print(f"⚠️ Errore su {full_path}: {e}")

    return function_map

if __name__ == "__main__":
    print("🔍 Scanning for duplicate function definitions...\n")
    functions = find_function_defs(PROJECT_DIR)

    duplicates = {k: v for k, v in functions.items() if len(v) > 1}

    if not duplicates:
        print("✅ Nessuna funzione duplicata trovata!")
    else:
        print("🚨 Funzioni duplicate trovate:")
        for func, files in duplicates.items():
            print(f"\n🌀 {func} definita {len(files)} volte in:")
            for path in files:
                print(f"  └── {path}")
