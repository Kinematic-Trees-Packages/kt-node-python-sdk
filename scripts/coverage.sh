#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
mkdir -p build/coverage

python -m coverage erase
python -m coverage run -m pytest -q tests
python -m coverage report
python -m coverage xml
python -m coverage json

echo "Coverage XML: build/coverage/coverage.xml"
echo "Coverage JSON: build/coverage/coverage.json"
