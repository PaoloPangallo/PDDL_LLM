#!/bin/bash
set -e

WORKDIR=$1  # La cartella della run, es. uploads/<session_id>
DOMAIN="$WORKDIR/domain.pddl"
PROBLEM="$WORKDIR/problem.pddl"
PLANNER=/home/paolop/downward/fast-downward.py
VAL_BIN=$HOME/VAL/build/bin/Validate

# Estrai il nome del dominio dal file domain.pddl
DOMAIN_NAME=$(grep -i "define (domain" "$DOMAIN" | sed 's/.*(domain[[:space:]]*\([^ )]*\).*/\1/')
if [ -z "$DOMAIN_NAME" ]; then
  echo "❌ Impossibile estrarre il nome del dominio da $DOMAIN"
  exit 1
fi

# Euristica
if [ -f "$WORKDIR/heuristic.txt" ]; then
  HEURISTIC=$(cat "$WORKDIR/heuristic.txt")
else
  HEURISTIC="lazy_greedy([ff()])"
fi

echo "==> Eseguo Fast Downward su $DOMAIN $PROBLEM con $HEURISTIC (dominio: $DOMAIN_NAME)"

# Pulizia dei vecchi file nella cartella della run
rm -f "$WORKDIR/sas_plan" "$WORKDIR/plan.txt" "$WORKDIR/plan.csv" "$WORKDIR/plan.json" "$WORKDIR/plan.soln" "$WORKDIR/validation.txt"

# Esegui il planner
python3 "$PLANNER" "$DOMAIN" "$PROBLEM" --search "$HEURISTIC"

if [ -f sas_plan ]; then
  mv sas_plan "$WORKDIR/plan.txt"
  echo "✅ Piano salvato in $WORKDIR/plan.txt"

  # Formatta ed esporta il piano in JSON e CSV, passando anche il nome del dominio
  python3 "$(dirname "$0")/format_plan.py" "$WORKDIR/plan.txt" "$WORKDIR" "$DOMAIN_NAME"

  # Validazione con VAL (opzionale)
  if [ -x "$VAL_BIN" ]; then
    echo "🔍 Validazione..."
    cp "$WORKDIR/plan.txt" "$WORKDIR/plan.soln"
    "$VAL_BIN" "$DOMAIN" "$PROBLEM" "$WORKDIR/plan.soln" > "$WORKDIR/validation.txt" 2>&1 \
      && echo "✅ Validazione completata" \
      || echo "⚠️  Validazione fallita. Controlla $WORKDIR/validation.txt"
  fi
else
  echo "❌ Nessun piano trovato."
fi
