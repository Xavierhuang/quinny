#!/usr/bin/env bash
# QuinnyBench end-to-end reproduce script.
#
# From a fresh clone:
#   cd quinnybench
#   cp .env.example .env       # fill in provider keys
#   ./reproduce.sh
#
# What it does, in order:
#   1. Creates a Python venv (idempotent).
#   2. Installs pytest + whichever provider SDKs match keys you've set.
#   3. Runs the benchmark for every configured provider × 40 tasks × 3 tracks
#      (code-from-md, code-from-qn, qn-from-md). Set MODES to run a subset.
#   4. Renders the static site to viz/out/ with all tracks side-by-side.
#   5. Prints the aggregate table.
#
# Cost note: 3 tracks means 3× the model calls. Override with e.g.
#   MODES="code-from-md" ./reproduce.sh
# to run the baseline track only.
#
# Everything except the model calls is deterministic. Re-runs against the same
# providers land the same aggregate ± any provider-side non-determinism.
set -euo pipefail

# --- venv ---------------------------------------------------------------
if [ ! -d .venv ]; then
    echo "→ creating .venv"
    python3 -m venv .venv
fi
PY=.venv/bin/python
PIP=.venv/bin/pip

echo "→ installing runtime deps (pytest)"
"$PIP" install -q pytest

# --- load .env if present ----------------------------------------------
if [ -f .env ]; then
    set -o allexport
    # shellcheck disable=SC1091
    . ./.env
    set +o allexport
fi

# --- pick providers by which keys are set -------------------------------
declare -a RUNS=()   # provider|model pairs to actually run
add_run() { RUNS+=("$1|$2"); }

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    "$PIP" install -q "anthropic>=0.40.0"
    add_run anthropic claude-opus-4-7
    add_run anthropic claude-sonnet-4-6
fi
if [ -n "${OPENAI_API_KEY:-}" ]; then
    "$PIP" install -q "openai>=1.50.0"
    add_run openai gpt-4o
    add_run openai o3
fi
if [ -n "${GOOGLE_API_KEY:-}" ]; then
    "$PIP" install -q "google-genai>=0.3.0"
    add_run google gemini-2.5-pro
fi
if [ -n "${XAI_API_KEY:-}" ]; then
    "$PIP" install -q "openai>=1.50.0"       # xai reuses openai SDK
    add_run xai grok-4
fi
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
    "$PIP" install -q "openai>=1.50.0"
    add_run deepseek deepseek-chat
fi
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    "$PIP" install -q "openai>=1.50.0"
    add_run openrouter moonshotai/kimi-k2
fi

if [ ${#RUNS[@]} -eq 0 ]; then
    echo "No provider keys detected in .env — nothing to run." >&2
    echo "Copy .env.example to .env and fill in at least one key." >&2
    exit 2
fi

# --- run the grid -------------------------------------------------------
RUN_DIR="results/$(date -u +%Y-%m-%d-%H%M%S)"
mkdir -p "$RUN_DIR"
echo "→ writing results to $RUN_DIR"

# Modes to run — comma or space separated. Defaults to all three tracks.
MODES="${MODES:-code-from-md code-from-qn qn-from-md}"
MODES="${MODES//,/ }"

for pair in "${RUNS[@]}"; do
    provider="${pair%%|*}"
    model="${pair##*|}"
    for mode in $MODES; do
        echo "→ $provider : $model [$mode]"
        "$PY" -m runner.run --provider "$provider" --model "$model" \
                            --mode "$mode" --run-dir "$RUN_DIR"
    done
done

# --- render the site + print summary -----------------------------------
"$PY" -m viz.build "$RUN_DIR" -o viz/out
echo
"$PY" -m runner.score "$RUN_DIR"
echo
echo "site:   file://$(pwd)/viz/out/index.html"
echo "raw:    $RUN_DIR/index.json"
