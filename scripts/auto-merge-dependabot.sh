#!/usr/bin/env bash
set -euo pipefail

head_sha=${1:?usage: auto-merge-dependabot.sh HEAD_SHA}
repository=${GITHUB_REPOSITORY:?}

pull_requests=$(gh api "repos/$repository/commits/$head_sha/pulls")
pull_number=$(jq -er --arg head_sha "$head_sha" '
  [
    .[]
    | select(
        .state == "open"
        and .base.ref == "main"
        and .head.sha == $head_sha
        and .user.login == "dependabot[bot]"
      )
  ]
  | if length == 1 then .[0].number else error("expected one open Dependabot pull request") end
' <<< "$pull_requests")

gh pr checks "$pull_number" --repo "$repository" --required
merge_state=$(gh pr view "$pull_number" --repo "$repository" \
  --json mergeStateStatus --jq '.mergeStateStatus')
if [[ "$merge_state" == BEHIND ]]; then
  gh api "repos/$repository/pulls/$pull_number/update-branch" \
    --method PUT -f "expected_head_sha=$head_sha"
  exit 0
fi

gh pr review "$pull_number" --repo "$repository" --approve
gh pr merge "$pull_number" --repo "$repository" --auto --squash \
  --match-head-commit "$head_sha"
