#!/usr/bin/env bash
set -euo pipefail
: "${KTM_BUILD_OUTPUT:?KTM_BUILD_OUTPUT is required}"
mkdir -p "$KTM_BUILD_OUTPUT"
cp -a boilerplate "$KTM_BUILD_OUTPUT/boilerplate"
