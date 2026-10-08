#!/usr/bin/env bash
set -euo pipefail

# Standalone planner wrapper: paths are independent of the working directory.
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <session_directory>" >&2
  exit 2
fi

WORKDIR="$(realpath "$1")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLANNER="\${FAST_DOWNWARD_PATH:-$PROJECT_DIR/downward/fast-downward.py}"
VAL_BIN="\${VAL_BIN:-$HOME/VAL/build/bin/Validate}"
PYTHON_BIN="\${PYTHON_BIN:-python3}"

DOMAIN="$WORKDIR/domain.pddl"
PROBLEM="$WORKDIR/problem.pddl"
PLAN="$WORKDIR/plan.txt"

if [ ! -f "$PLANNER" ]; then
  echo "Fast Downward missing: set FAST_DOWNWARD_PATH to fast-downward.py" >&2
  exit 127
fi
if [ ! -f "$DOMAIN" ] || [ ! -f "$PROBLEM" ]; then
  echo "Missing PDDL files in: $WORKDIR" >&2
  exit 2
fi

DOMAIN_NAME="$(sed -nE 's/.*\([Dd][Oo][Mm][Aa][Ii][Nn][[:space:]]+([^[:space:])]+)\).*/\1/p' "$DOMAIN" | head -n1)"
if [ -z "$DOMAIN_NAME" ]; then
  echo "Cannot extract PDDL domain name from $DOMAIN" >&2
  exit 2
fi

HEURISTIC="lazy_greedy([ff()])"
if [ -f "$WORKDIR/heuristic.txt" ]; then
  HEURISTIC="$(cat "$WORKDIR/heuristic.txt")"
fi

rm -f "$WORKDIR/plan.txt" "$WORKDIR/plan.csv" "$WORKDIR/plan.json" \
  "$WORKDIR/plan.soln" "$WORKDIR/validation.txt"

echo "Running Fast Downward on $DOMAIN / $PROBLEM ($DOMAIN_NAME)"
"$PYTHON_BIN" "$PLANNER" --plan-file "$PLAN" "$DOMAIN" "$PROBLEM" --search "$HEURISTIC"

if [ ! -f "$PLAN" ]; then
  echo "No plan produced for task." >&2
  exit 1
fi

echo "Plan found: $PLAN"
"$PYTHON_BIN" "$SCRIPT_DIR/format_plan.py" "$PLAN" "$WORKDIR" "$DOMAIN_NAME"

if [ -x "$VAL_BIN" ]; then
  cp "$PLAN" "$WORKDIR/plan.soln"
  if "$VAL_BIN" "$DOMAIN" "$PROBLEM" "$WORKDIR/plan.soln" > "$WORKDIR/validation.txt" 2>&1; then
    echo "Plan validated with VAL"
  else
    echo "VAL rejected the plan; see $WORKDIR/validation.txt" >&2
    exit 1
  fi
fi
