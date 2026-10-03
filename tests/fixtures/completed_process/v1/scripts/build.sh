#!/usr/bin/env bash
set -euo pipefail

out="${KTM_BUILD_OUTPUT:-build/ktm-output}"
rm -rf "$out"
mkdir -p "$out"
cp -a package.ktm.json runtime.json src "$out/"
