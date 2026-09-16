#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

python -m pytest -q tests/test_documentation_examples.py
python -m mkdocs build --strict --clean
python scripts/validate_docs.py

mkdir -p build/docs-artifacts
tar --sort=name --mtime='UTC 2026-01-01' --owner=0 --group=0 --numeric-owner \
  -cf - -C build/docs v0.2 | gzip -n > build/docs-artifacts/kt-node-python-sdk-docs-v0.2.tar.gz

echo "Documentation artifact: build/docs-artifacts/kt-node-python-sdk-docs-v0.2.tar.gz"
