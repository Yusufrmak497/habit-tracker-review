#!/usr/bin/env bash
# Deterministic guardrails: the same commands run locally and in CI.
# Exits non-zero if formatting, lint, or tests fail.
set -uo pipefail
cd "$(dirname "$0")/.."
BIN=".venv/bin"; [ -x "$BIN/pytest" ] || BIN="$(dirname "$(command -v pytest)")"
status=0
echo "▶ black --check"; "$BIN/black" --check --diff . || status=1
echo "▶ ruff check";    "$BIN/ruff" check .            || status=1
echo "▶ pytest";        "$BIN/pytest"                  || status=1
[ "$status" -eq 0 ] && echo "✔ guardrails passed" || echo "✖ guardrails FAILED" >&2
exit "$status"
