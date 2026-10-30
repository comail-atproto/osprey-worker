#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT

cat > "$test_dir/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

case "$1 $2" in
  "push ghcr.io/comail-atproto/osprey-worker:build-"*) ;;
  "image inspect")
    if [[ "$*" == *RepoDigests* ]]; then
      printf '["ghcr.io/comail-atproto/osprey-worker@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]\n'
    else
      printf 'sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\n'
    fi
    ;;
  "manifest inspect")
    printf '{"config":{"digest":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}}\n'
    ;;
  *)
    printf 'unexpected docker invocation: %s\n' "$*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$test_dir/docker"

cat > "$test_dir/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

case "$*" in
  "rev-parse HEAD") printf 'dddddddddddddddddddddddddddddddddddddddd\n' ;;
  "-C upstream rev-parse HEAD") printf 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\n' ;;
  "ls-tree HEAD upstream") printf '160000 commit eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\tupstream\n' ;;
  "-C upstream rev-parse HEAD^{tree}") printf 'ffffffffffffffffffffffffffffffffffffffff\n' ;;
  *) printf 'unexpected git invocation: %s\n' "$*" >&2; exit 1 ;;
esac
EOF
chmod +x "$test_dir/git"

cat > "$test_dir/sha256sum" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '9999999999999999999999999999999999999999999999999999999999999999  %s\n' "$1"
EOF
chmod +x "$test_dir/sha256sum"

export PATH="$test_dir:$PATH"
export GITHUB_REPOSITORY=comail-atproto/osprey-worker
export GITHUB_REF=refs/heads/main
export GITHUB_SHA=dddddddddddddddddddddddddddddddddddddddd
export GITHUB_RUN_ID=123
export GITHUB_SERVER_URL=https://github.com
export GITHUB_OUTPUT="$test_dir/output"
export RUNNER_TEMP="$test_dir"

(cd "$repo_root" && bash scripts/publish.sh)

jq -e '
  .image == "ghcr.io/comail-atproto/osprey-worker@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  and .config_id == "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
' "$test_dir/provenance.json" >/dev/null
