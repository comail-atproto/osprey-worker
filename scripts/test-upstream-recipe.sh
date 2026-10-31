#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
recipe="$(cat upstream/osprey_worker/Dockerfile)"
output="$(mktemp)"
trap 'rm -f "$output"' EXIT

UPSTREAM_DOCKERFILE="$recipe" docker buildx bake --print worker > "$output"
jq -e --arg recipe "$recipe" '(.target.upstream["dockerfile-inline"] | gsub("\\$\\$\\{"; "${")) == ($recipe | gsub("wget ssh &&"; "wget openssh-client &&"))' "$output" >/dev/null

if UPSTREAM_DOCKERFILE='unexpected upstream recipe' docker buildx bake --print worker >/dev/null 2>&1; then
  echo 'Changed upstream recipe must be rejected.' >&2
  exit 1
fi
if UPSTREAM_DOCKERFILE="$recipe
$recipe" docker buildx bake --print worker >/dev/null 2>&1; then
  echo 'Ambiguous upstream recipe must be rejected.' >&2
  exit 1
fi
