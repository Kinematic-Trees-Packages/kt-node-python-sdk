#!/usr/bin/env bash
set -euo pipefail
out="${KTM_BUILD_OUTPUT:-build/ktm-output}"
rm -rf "$out"
mkdir -p "$out/python"
cp -a README.md package.ktm.json scripts pyproject.toml src examples tests "$out/python"/
find "$out/python" -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
find "$out/python" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
echo "Built {{KTM_CREATE_PROJECT_NAME}} Python runtime/source package into $out/python"
