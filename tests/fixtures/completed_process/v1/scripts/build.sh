#!/usr/bin/env bash
set -euo pipefail

out="${KTM_BUILD_OUTPUT:-build/ktm-output}"
rm -rf "$out"
mkdir -p "$out/runtime"
cp -a package.ktm.json runtime src "$out/runtime/"
