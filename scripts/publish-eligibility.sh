#!/usr/bin/env bash
set -euo pipefail

event=${1:?event required}
actor=${2:?actor required}
if [[ "$event" == push && "$actor" == 'comail-release[bot]' ]]; then
  printf 'false\n'
else
  printf 'true\n'
fi
