#!/usr/bin/env bash
set -euo pipefail

check() {
  local expected=$1 event=$2 actor=$3
  local result
  result=$(bash scripts/publish-eligibility.sh "$event" "$actor")
  [[ "$result" == "$expected" ]] || {
    printf 'event=%s actor=%s: expected %s, got %s\n' "$event" "$actor" "$expected" "$result" >&2
    exit 1
  }
}

check false push 'comail-release[bot]'
check true push example-user
check true push 'dependabot[bot]'
check true workflow_dispatch 'comail-release[bot]'
check true workflow_dispatch example-user
