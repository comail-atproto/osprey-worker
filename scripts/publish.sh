#!/usr/bin/env bash
set -euo pipefail

[[ "${GITHUB_REPOSITORY:-}" == comail-atproto/osprey-worker ]]
[[ "${GITHUB_REF:-}" == refs/heads/main ]]
[[ "$(git rev-parse HEAD)" == "${GITHUB_SHA:-}" ]]
: "${RUNNER_TEMP:?}" "${GITHUB_RUN_ID:?}" "${GITHUB_OUTPUT:?}"
image="ghcr.io/comail-atproto/osprey-worker:build-$GITHUB_SHA"
[[ "$(git -C upstream rev-parse HEAD)" == "$(git ls-tree HEAD upstream | awk '{print $3}')" ]]

docker push "$image"
digest=$(docker image inspect "$image" --format '{{json .RepoDigests}}' \
  | jq -er '.[] | select(startswith("ghcr.io/comail-atproto/osprey-worker@")) | split("@")[1]')
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
config_id=$(docker manifest inspect "$image" | jq -er '.config.digest')
[[ "$config_id" =~ ^sha256:[0-9a-f]{64}$ ]]
jq -n \
  --arg image "ghcr.io/comail-atproto/osprey-worker@$digest" \
  --arg config_id "$config_id" \
  --arg source_revision "$(git -C upstream rev-parse HEAD)" \
  --arg source_tree "$(git -C upstream rev-parse 'HEAD^{tree}')" \
  --arg recipe_sha256 "$(sha256sum upstream/osprey_worker/Dockerfile | awk '{print $1}')" \
  --arg lock_sha256 "$(sha256sum upstream/uv.lock | awk '{print $1}')" \
  --arg runtime_recipe_sha256 "$(sha256sum Dockerfile | awk '{print $1}')" \
  --arg base_recipe_sha256 "$(sha256sum Dockerfile.python | awk '{print $1}')" \
  --arg repository "$GITHUB_REPOSITORY" \
  --arg ref "$GITHUB_REF" \
  --arg commit "$GITHUB_SHA" \
  --argjson run_id "$GITHUB_RUN_ID" \
  --arg url "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" \
  '{image:$image,config_id:$config_id,source_revision:$source_revision,source_tree:$source_tree,recipe_sha256:$recipe_sha256,lock_sha256:$lock_sha256,runtime_recipe_sha256:$runtime_recipe_sha256,base_recipe_sha256:$base_recipe_sha256,builder:{repository:$repository,ref:$ref,commit:$commit,run_id:$run_id,url:$url}}' \
  > "$RUNNER_TEMP/provenance.json"
printf 'digest=%s\n' "$digest" >> "$GITHUB_OUTPUT"
