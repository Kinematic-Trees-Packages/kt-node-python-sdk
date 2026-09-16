#!/usr/bin/env bash
set -euo pipefail
: "${KTM_BUILD_OUTPUT:?KTM_BUILD_OUTPUT is required}"
rm -rf "${KTM_BUILD_OUTPUT:?}"/*
mkdir -p "$KTM_BUILD_OUTPUT"
cp -a boilerplate "$KTM_BUILD_OUTPUT/boilerplate"
cp -a pyproject.toml "$KTM_BUILD_OUTPUT/pyproject.toml"
cp -a mkdocs.yml "$KTM_BUILD_OUTPUT/mkdocs.yml"
cp -a python "$KTM_BUILD_OUTPUT/python"
cp -a tests "$KTM_BUILD_OUTPUT/tests"
cp -a docs "$KTM_BUILD_OUTPUT/docs"
cp -a examples "$KTM_BUILD_OUTPUT/examples"
mkdir -p "$KTM_BUILD_OUTPUT/scripts"
cp -a scripts/package.sh scripts/docs.sh scripts/validate_docs.py "$KTM_BUILD_OUTPUT/scripts/"
if [ -d share ]; then cp -a share "$KTM_BUILD_OUTPUT/share"; fi
if [ -f package-hygiene.txt ]; then cp -a package-hygiene.txt "$KTM_BUILD_OUTPUT/package-hygiene.txt"; fi
find "$KTM_BUILD_OUTPUT" -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache -o -name node_modules \) -prune -exec rm -rf {} +
find "$KTM_BUILD_OUTPUT" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
