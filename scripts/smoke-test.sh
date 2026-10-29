#!/usr/bin/env bash
set -euo pipefail

image=${1:?usage: smoke-test.sh IMAGE}
[[ "$(docker image inspect "$image" --format '{{.Architecture}}')" == amd64 ]]
[[ "$(docker image inspect "$image" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" == "$(git rev-parse HEAD)" ]]
[[ "$(docker image inspect "$image" --format '{{index .Config.Labels "at.comail.upstream-revision"}}')" == "$(git -C upstream rev-parse HEAD)" ]]

docker run --rm --network none --cpus 1 --memory 512m --pids-limit 128 \
  --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint uv "$image" \
  run python3.11 osprey_worker/src/osprey/worker/cli/sinks.py --help
