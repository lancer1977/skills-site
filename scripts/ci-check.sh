#!/usr/bin/env bash
# Tier 1 check: unit tests, then an offline generator build into build/ci-site.
# The build runs from a copy of scripts/ whose categories.json is replaced by a
# fixture, so it never reads ~/.claude/skills, never publishes fixture data and
# never touches the committed site/ output. Runs identically in CI and locally.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

PYTHON="${PYTHON:-python3}"
WORK="build/ci-scripts"
OUT="build/ci-site"

echo "==> unit tests"
"$PYTHON" -m unittest discover -s scripts -p 'test_*.py'

echo "==> offline generator build"
rm -rf "$WORK" "$OUT"
mkdir -p build
cp -r scripts "$WORK"
cp scripts/fixtures/categories.json "$WORK/categories.json"
"$PYTHON" "$WORK/generate.py" --skills-dir scripts/fixtures/skills --out "$OUT"

echo "==> assert build output"
for f in "$OUT/index.html" "$OUT/fixture-skill/index.html" "$OUT/assets/style.css"; do
  if [ ! -s "$f" ]; then
    echo "ci-check: missing or empty output: $f" >&2
    exit 1
  fi
done
grep -q "fixture-skill" "$OUT/index.html" || { echo "ci-check: catalog does not list fixture-skill" >&2; exit 1; }

echo "ci-check: OK"
