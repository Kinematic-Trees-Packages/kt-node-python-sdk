#!/usr/bin/env bash
set -euo pipefail
out="${KTM_BUILD_OUTPUT:-build/ktm-output}"
rm -rf "$out"
mkdir -p "$out/runtime" "$out/source"
cp -a README.md package.ktm.json pyproject.toml src "$out/runtime"/
cp -a README.md package.ktm.json pyproject.toml scripts src examples tests "$out/source"/
find "$out" -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
find "$out" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
echo "Built {{KTM_CREATE_PROJECT_NAME}} Python runtime and development source sets into $out"
