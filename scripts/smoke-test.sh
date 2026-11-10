#!/usr/bin/env bash
set -euo pipefail

image=${1:?usage: smoke-test.sh IMAGE}
[[ "$(docker image inspect "$image" --format '{{.Architecture}}')" == amd64 ]]
[[ "$(docker image inspect "$image" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" == "$(git rev-parse HEAD)" ]]
[[ "$(docker image inspect "$image" --format '{{index .Config.Labels "upstream.revision"}}')" == "$(git -C upstream rev-parse HEAD)" ]]

temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT
cp upstream/pyproject.toml upstream/uv.lock "$temp_dir/"
git -C "$temp_dir" apply "$PWD/patches/kafka-python-2.3.3.patch"
expected_lock=$(sha256sum "$temp_dir/uv.lock" | awk '{print $1}')
expected_patch=$(sha256sum patches/kafka-python-2.3.3.patch | awk '{print $1}')
actual_lock=$(docker run --rm --network none --entrypoint sha256sum "$image" /osprey/uv.lock | awk '{print $1}')
actual_patch=$(docker run --rm --network none --entrypoint sha256sum "$image" /usr/local/share/osprey-kafka.patch | awk '{print $1}')
[[ "$actual_lock" == "$expected_lock" && "$actual_patch" == "$expected_patch" ]]
[[ "$(docker run --rm --network none --entrypoint /osprey/.venv/bin/python "$image" -c 'import kafka; print(kafka.__version__)')" == 2.3.3 ]]

docker run --rm --network none --cpus 1 --memory 512m --pids-limit 128 \
  --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint uv "$image" \
  run python3.11 osprey_worker/src/osprey/worker/cli/sinks.py --help
