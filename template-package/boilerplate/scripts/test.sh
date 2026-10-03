#!/usr/bin/env bash
set -euo pipefail

split_paths() {
  local value=${1:-}
  IFS=':' read -r -a __paths <<<"$value"
  for p in "${__paths[@]}"; do
    [[ -n "$p" ]] && printf '%s\n' "$p"
  done
}

find_in_path_list() {
  local env_name=$1
  local rel=$2
  local value=${!env_name:-}
  while IFS= read -r root; do
    [[ -e "$root/$rel" ]] && return 0
  done < <(split_paths "$value")
  return 1
}

require_kt_node_build_env() {
  local missing=0
  if ! find_in_path_list CPATH kt_node.h; then
    echo "kt-node header kt_node.h not found in CPATH; run through KTM so kt-node includePaths are composed" >&2
    missing=1
  fi
  if ! find_in_path_list LIBRARY_PATH libkt_node.so && ! find_in_path_list LIBRARY_PATH libkt_node.a && ! find_in_path_list LD_LIBRARY_PATH libkt_node.so; then
    echo "kt-node library not found in LIBRARY_PATH/LD_LIBRARY_PATH; run through KTM so kt-node libraryPaths are composed" >&2
    missing=1
  fi
  if [[ $missing -ne 0 ]]; then
    exit 2
  fi
}

cflags_from_cpath() {
  while IFS= read -r root; do printf ' -I%s' "$root"; done < <(split_paths "${CPATH:-}")
}

ldflags_from_library_path() {
  while IFS= read -r root; do printf ' -L%s' "$root"; done < <(split_paths "${LIBRARY_PATH:-}")
}

require_kt_node_build_env
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_src="$project_root/src"
export PYTHONPATH="$project_src${PYTHONPATH:+:$PYTHONPATH}"

python3 -m py_compile "$project_src"/{{KTM_CREATE_MODULE_NAME}}/*.py
python3 - <<'PY'
import kt.messages
from kt.messages import *  # noqa: F403

exports = set(kt.messages.__all__)
assert {"codec_for", "registered_datatypes", "string_sample", "vision_sample"} <= exports
assert all(name in globals() for name in exports)
print("kt-messages wildcard import passed")
PY
python3 - <<'PY'
from {{KTM_CREATE_MODULE_NAME}} import Process

assert Process.__mro__[1].__name__ == "Node", "generated Process must inherit the public SDK Node"
print("Generated Process imports through the public Python SDK")
PY
echo "Python process source smoke passed"
