#!/usr/bin/env bash
set -euo pipefail

cd "${1:?Directory containing worker.tar is required}"
sha256sum --check worker.tar.sha256

curl --fail --silent --show-error --location --retry 2 --max-time 60 \
  --output osv-scanner \
  https://github.com/google/osv-scanner/releases/download/v2.7.1/osv-scanner_linux_amd64
printf '%s  %s\n' fb7dab19a8bd9bbe5c3189f09d4b7ee1820c9553a23bac202648a56efd2f6ee8 osv-scanner |
  sha256sum --check
chmod +x osv-scanner
./osv-scanner --version | tee worker-osv-version.txt

result=0
./osv-scanner scan image --archive worker.tar --format json --output-file worker-osv.json \
  >worker-osv.log 2>&1 ||
  result=$?
case "$result" in
  0) ;;
  1) echo "OSV reported vulnerabilities. Review worker-osv.json." ;;
  *) exit "$result" ;;
esac
jq -e 'type == "object" and has("results")' worker-osv.json >/dev/null
