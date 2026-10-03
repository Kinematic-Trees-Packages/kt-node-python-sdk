#!/usr/bin/env bash
set -euo pipefail
out="${KTM_BUILD_OUTPUT:-build/ktm-output}"
rm -rf "$out"
mkdir -p "$out"
cp -a package.ktm.json runtime.json pyproject.toml src "$out"/
mkdir -p "$out/development"
cp -a README.md docs scripts "$out/development"/
find "$out" -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
find "$out" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
echo "Built {{KTM_CREATE_PROJECT_NAME}} flat Python source package into $out"
