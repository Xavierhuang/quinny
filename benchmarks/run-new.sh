#!/usr/bin/env sh
# Run the three benchmark harnesses added by verify_{oss_bugs,scale,subtle}.
# Existing benchmarks (usability/realworld/determinism/crosslang/loop) are
# unchanged — this script is just for the new ones.
#
# Env:
#   QUINNY_MODEL       (default: claude-haiku-4-5)
#   ANTHROPIC_API_KEY  or ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL
#   QUINNY_SCALES      restrict the scale sweep, e.g. "10,25"
#
# Skips subtle-bugs on the first run if there's no committed suite — pass
# --emit-subtle to generate one, or point at an existing one via env
# SUBTLE_SUITE=<path>.

set -eu
cd "$(dirname "$0")/.."

: "${QUINNY_MODEL:=claude-haiku-4-5}"
export QUINNY_MODEL

dry=0
emit_subtle=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)     dry=1 ;;
    --emit-subtle) emit_subtle=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [ "$dry" = "0" ] && [ -z "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}" ]; then
  echo "error: set ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL)"
  echo "       or pass --dry-run to preview without calling the API."
  exit 2
fi

dryflag=""
[ "$dry" = "1" ] && dryflag="--dry-run"

echo "==============================================================="
echo "1/3  OSS-bug reproduction  (verify_oss_bugs.py)"
echo "==============================================================="
"${PYTHON:-python3}" benchmarks/verify_oss_bugs.py $dryflag

echo
echo "==============================================================="
echo "2/3  Scale sweep           (verify_scale.py)"
echo "==============================================================="
"${PYTHON:-python3}" benchmarks/verify_scale.py $dryflag

echo
echo "==============================================================="
echo "3/3  Subtle-bug defects    (verify_subtle.py)"
echo "==============================================================="
subtle_suite="${SUBTLE_SUITE:-benchmarks/fixtures/subtle/suite.py}"
if [ "$dry" = "1" ]; then
  "${PYTHON:-python3}" benchmarks/verify_subtle.py --dry-run
elif [ ! -f "$subtle_suite" ] && [ "$emit_subtle" = "1" ]; then
  echo "[emit] no committed suite at $subtle_suite — emitting one now"
  "${PYTHON:-python3}" benchmarks/verify_subtle.py --emit
elif [ ! -f "$subtle_suite" ]; then
  echo "[skip] no committed suite at $subtle_suite"
  echo "       run once with --emit-subtle to generate it, then re-run"
else
  "${PYTHON:-python3}" benchmarks/verify_subtle.py --suite "$subtle_suite"
fi
