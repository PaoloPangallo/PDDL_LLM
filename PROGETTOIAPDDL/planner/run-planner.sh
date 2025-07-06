#!/bin/bash
set -e

# 1) directory di lavoro (uploads/<session_id>)
WORKDIR=$1
[ -n "$WORKDIR" ] || { echo "Uso: $0 <uploads/session_id>"; exit 1; }
DOMAIN="$WORKDIR/domain.pddl"
PROBLEM="$WORKDIR/problem.pddl"

# 2) path a Fast Downward
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
FD_ROOT="$SCRIPTS_DIR/../external/downward"
BUILD_DIR="$FD_ROOT/builds/release"

#  se manca il translator, ricompila senza argomenti (incluso src/translate)
if [ ! -f "$FD_ROOT/src/translate/translate.py" ]; then
  echo "⚙️  Traduttore mancante, ricompilo…"
  (cd "$FD_ROOT" && python3 build.py)
fi

FASTDOWNWARD_PY="$FD_ROOT/fast-downward.py"
TRANSLATE_PY="$FD_ROOT/src/translate/translate.py"

# 3) validatore VAL (apt oppure build da te)
if command -v validate >/dev/null 2>&1; then
  VAL_BIN="validate"
else
  VAL_BIN="$HOME/VAL/build/bin/Validate"
fi

# 4) estrai nome dominio
DOMAIN_NAME=$(grep -i "define (domain" "$DOMAIN" \
    | sed -E 's/.*\(domain[[:space:]]*([^ )]*).*/\1/')
[ -n "$DOMAIN_NAME" ] || { echo "❌ Nome dominio non trovato in $DOMAIN"; exit 1; }

# 5) euristica
if [ -f "$WORKDIR/heuristic.txt" ]; then
  HEURISTIC=$(<"$WORKDIR/heuristic.txt")
else
  HEURISTIC="lazy_greedy([ff()])"
fi

echo "==> Fast Downward su $DOMAIN e $PROBLEM"
echo "       euristica: $HEURISTIC (dominio: $DOMAIN_NAME)"

# 6) pulisci output precedenti
rm -f "$WORKDIR"/{sas_plan,plan.txt,plan.csv,plan.json,plan.soln,validation.txt}

# 7) esegui planner
python3 "$FASTDOWNWARD_PY" "$DOMAIN" "$PROBLEM" --search "$HEURISTIC"

# 8) post-process
if [ -f sas_plan ]; then
  mv sas_plan "$WORKDIR/plan.txt"
  echo "✅ Piano in $WORKDIR/plan.txt"

  # formatta in CSV/JSON
  python3 "$SCRIPTS_DIR/format_plan.py" \
    "$WORKDIR/plan.txt" "$WORKDIR" "$DOMAIN_NAME"

  # validazione se disponibile
  if command -v validate >/dev/null 2>&1 || [ -x "$VAL_BIN" ]; then
    echo "🔍 Validazione con VAL…"
    cp "$WORKDIR/plan.txt" "$WORKDIR/plan.soln"
    $VAL_BIN "$DOMAIN" "$PROBLEM" "$WORKDIR/plan.soln" \
      > "$WORKDIR/validation.txt" 2>&1 \
      && echo "✅ Validazione OK" \
      || echo "⚠️ Validazione FALLITA (vedi validation.txt)"
  fi
else
  echo "❌ Nessun piano trovato."
fi