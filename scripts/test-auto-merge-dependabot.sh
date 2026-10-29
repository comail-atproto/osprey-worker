#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT

cat > "$test_dir/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "$1" == api && "$2" == */pulls/7/update-branch ]]; then
  printf '%s\n' "$*" >> "$MOCK_LOG"
  exit 0
fi

if [[ "$1" == api ]]; then
  printf '[{"number":7,"state":"open","base":{"ref":"main"},"head":{"sha":"%s"},"user":{"login":"%s"}}]\n' \
    "${MOCK_HEAD_SHA:-abc123}" "${MOCK_AUTHOR:-dependabot[bot]}"
  exit 0
fi

if [[ "$1 $2" == "pr checks" ]]; then
  exit "${MOCK_CHECKS_EXIT:-0}"
fi

if [[ "$1 $2" == "pr view" ]]; then
  printf '%s\n' "${MOCK_MERGE_STATE:-BLOCKED}"
  exit 0
fi

printf '%s\n' "$*" >> "$MOCK_LOG"
EOF
chmod +x "$test_dir/gh"

export PATH="$test_dir:$PATH"
export GITHUB_REPOSITORY=example/osprey-worker
export MOCK_LOG="$test_dir/calls"

bash "$script_dir/auto-merge-dependabot.sh" abc123
diff -u <(printf '%s\n' \
  'pr review 7 --repo example/osprey-worker --approve' \
  'pr merge 7 --repo example/osprey-worker --squash --match-head-commit abc123' \
  'workflow run image.yml --repo example/osprey-worker --ref main') "$MOCK_LOG"

: > "$MOCK_LOG"
if MOCK_AUTHOR=someone bash "$script_dir/auto-merge-dependabot.sh" abc123 2>/dev/null; then
  echo "accepted a non-Dependabot pull request" >&2
  exit 1
fi
[[ ! -s "$MOCK_LOG" ]]

if MOCK_CHECKS_EXIT=1 bash "$script_dir/auto-merge-dependabot.sh" abc123 2>/dev/null; then
  echo "accepted a pull request with failed required checks" >&2
  exit 1
fi

: > "$MOCK_LOG"
MOCK_MERGE_STATE=BEHIND bash "$script_dir/auto-merge-dependabot.sh" abc123
diff -u <(printf '%s\n' \
  'api repos/example/osprey-worker/pulls/7/update-branch --method PUT -f expected_head_sha=abc123') "$MOCK_LOG"
