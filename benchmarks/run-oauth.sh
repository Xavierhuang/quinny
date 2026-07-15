#!/bin/sh
# Benchmark runner using the local Claude subscription (OAuth token from the
# Keychain) via the Anthropic SDK. Lets Quinny's SDK generator run on Claude
# models (haiku/sonnet/opus) without an API key. Draws on the Claude subscription.
set -eu
cd "$(dirname "$0")/.."

RAW=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null || true)
TOK=$(printf '%s' "$RAW" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("claudeAiOauth",{}).get("accessToken",""))' 2>/dev/null || true)
if [ -z "${TOK:-}" ]; then
  echo "ERROR: could not read Claude OAuth token from Keychain" >&2
  exit 2
fi
export ANTHROPIC_AUTH_TOKEN="$TOK"
export QUINNY_OAUTH=1
unset ANTHROPIC_BASE_URL || true
unset ANTHROPIC_API_KEY || true

exec .venv/bin/python scripts/bench.py "$@"
