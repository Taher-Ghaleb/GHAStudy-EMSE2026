#!/usr/bin/env bash
# Extract per-language GHA workflow YAML archives into data/workflows/.
# Run from anywhere; resolves paths relative to the repository root.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVES="$ROOT/data/archives"
WORKFLOWS="$ROOT/data/workflows"

mkdir -p "$WORKFLOWS"

flatten_inner() {
  local target="$1"
  local inner="$2"
  if [[ ! -d "$target/$inner" ]]; then
    return 0
  fi
  shopt -s dotglob nullglob
  for item in "$target/$inner"/*; do
    [[ -e "$item" ]] || continue
    local name
    name="$(basename "$item")"
    if [[ -e "$target/$name" ]]; then
      rm -rf "$item"
    else
      mv "$item" "$target/$name"
    fi
  done
  rm -rf "$target/$inner"
  echo "  Flattened ${inner}/ into $(basename "$target")/"
}

extract_one() {
  local archive="$1"
  local target="$2"
  local inner="$3"
  if [[ ! -f "$ARCHIVES/${archive}.zip" ]]; then
    echo "Missing archive: data/archives/${archive}.zip"
    return 1
  fi
  if [[ -d "$target/$inner" ]]; then
    flatten_inner "$target" "$inner"
    echo "Flattened existing extraction at $target"
    return 0
  fi
  if [[ -d "$target" ]] && find "$target" -type f \( -name '*.yml' -o -name '*.yaml' \) | grep -q .; then
    echo "Skipping ${archive}.zip - already extracted at $target"
    return 0
  fi
  mkdir -p "$target"
  echo "Extracting ${archive}.zip -> $target"
  unzip -q "$ARCHIVES/${archive}.zip" -d "$target"
  flatten_inner "$target" "$inner"
}

status=0
extract_one python_yml_files "$WORKFLOWS/python_yml_files" python || status=1
extract_one java_yml_files "$WORKFLOWS/java_yml_files" java || status=1
extract_one c++_yml_files "$WORKFLOWS/c++_yml_files" c++ || status=1

if [[ $status -eq 0 ]]; then
  echo ""
  echo "Done. Workflow YAMLs are available under data/workflows/"
fi

exit $status
