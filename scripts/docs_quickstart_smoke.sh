#!/usr/bin/env bash
set -euo pipefail

ktm_bin=${KTM_BIN:-ktm}
workspace=$(mktemp -d)
trap 'rm -rf "$workspace"' EXIT

cd "$workspace"
"$ktm_bin" create my-process \
  --language python \
  --namespace local-docs \
  --platform linux_20 \
  --non-interactive \
  --no-test
cd my-process
"$ktm_bin" dev --platform linux_20
"$ktm_bin" test --platform linux_20

echo "Documentation quick start passed in a disposable project"
