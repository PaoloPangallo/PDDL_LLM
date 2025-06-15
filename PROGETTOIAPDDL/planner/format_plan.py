import re
import json
import csv
import os
import sys

def load_action_costs(domain_name, workdir):
    config_filename = os.path.join(workdir, f"action_costs_{domain_name}.json")
    if os.path.exists(config_filename):
        with open(config_filename, "r") as f:
            return json.load(f)
    else:
        print(f"Attenzione: file {config_filename} non trovato. Uso mapping di default (0 per tutte le azioni).")
        return {}

def parse_plan(plan_file, action_costs):
    with open(plan_file, "r") as f:
        lines = f.readlines()

    steps = []
    cumulative_cost = 0.0
    total_cost = None

    for line in lines:
        line = line.strip()
        if line.startswith("; cost ="):
            match = re.search(r"; cost = ([0-9.]+)", line)
            if match:
                total_cost = float(match.group(1))
        elif line.startswith("("):
            action = re.sub(r"[()]", "", line)
            action_tokens = action.split()
            act = action_tokens[0].lower()

            # Default costo zero
            step_cost = 0.0

            cost_entry = action_costs.get(act, 0.0)

            if isinstance(cost_entry, dict):
                # Cerca il truck tra i parametri dell'azione
                for arg in action_tokens[1:]:
                    if arg in cost_entry:
                        step_cost = cost_entry[arg]
                        break
                else:
                    print(f"⚠️  Nessun truck trovato per azione '{act}' tra: {action_tokens}")
            else:
                step_cost = cost_entry

            cumulative_cost += step_cost

            steps.append({
                "step": len(steps) + 1,
                "action": action,
                "step_cost": step_cost,
                "cumulative_cost": cumulative_cost
            })

    return steps, total_cost

def export_csv(steps, filename="plan.csv"):
    fieldnames = ["step", "action", "step_cost", "cumulative_cost"]
    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for step in steps:
            writer.writerow(step)

def export_json(steps, total_cost, filename="plan.json"):
    plan_obj = {
        "steps": steps,
        "total_cost": total_cost
    }
    with open(filename, "w") as f:
        json.dump(plan_obj, f, indent=2)

def print_plan(steps, total_cost):
    print("📋 Piano formattato:\n")
    for step in steps:
        print(f"📍 {step['step']:>2}. {step['action']}  (Costo azione: {step['step_cost']}, Costo cumulativo: {step['cumulative_cost']})")
    if total_cost is not None:
        print(f"\n💰 Costo totale: {total_cost:.2f}")
    else:
        print("\n💰 Costo totale non trovato nel piano.")
    print("\n💾 Esportato in plan.csv e plan.json")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python format_plan.py <plan.txt> <workdir> <domain_name>")
        sys.exit(1)

    plan_txt_path = sys.argv[1]
    workdir = sys.argv[2]
    domain_name = sys.argv[3]

    action_costs = load_action_costs(domain_name, workdir)
    steps, total_cost = parse_plan(plan_txt_path, action_costs)
    export_csv(steps, filename=os.path.join(workdir, "plan.csv"))
    export_json(steps, total_cost, filename=os.path.join(workdir, "plan.json"))
    print_plan(steps, total_cost)
