#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

suite=${1:-all}
case "$suite" in
  unit|contract|template|integration)
    python -m pytest -q "tests/$suite"
    ;;
  all)
    python -m pytest -q tests
    ;;
  *)
    echo "usage: $0 [unit|contract|template|integration|all]" >&2
    exit 2
    ;;
esac
