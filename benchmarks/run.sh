#!/bin/sh
# Benchmark runner: loads LingModel (kimi) creds from Keychain, routes the SDK
# through the proxy, and runs bench.py with whatever args are passed through.
# Opus configs use the `claude` CLI's own auth and ignore these.
set -eu
cd "$(dirname "$0")/.."

TOK=$(security find-generic-password -s LingCode -a lingcode_auth_access_token -w 2>/dev/null || true)
if [ -z "${TOK:-}" ]; then
  echo "ERROR: could not read LingCode token from Keychain" >&2
  exit 2
fi
export ANTHROPIC_AUTH_TOKEN="$TOK"
export ANTHROPIC_BASE_URL="https://lingcode.dev/api/inference/anthropic"
export QUINNY_MODEL="kimi-k2.7"
unset ANTHROPIC_API_KEY || true

exec .venv/bin/python scripts/bench.py "$@"
