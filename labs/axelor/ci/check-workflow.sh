#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
lint_dir=$(mktemp -d "${RUNNER_TEMP:-/tmp}/ccm-actionlint.XXXXXX")
trap 'rm -rf "$lint_dir"' EXIT
curl --fail --location --silent --show-error \
  https://github.com/rhysd/actionlint/releases/download/v1.7.7/actionlint_1.7.7_linux_amd64.tar.gz \
  -o "$lint_dir/actionlint.tar.gz"
# Official v1.7.7 release checksums file, inspected over verified HTTPS.
printf '%s  %s\n' \
  023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757 \
  "$lint_dir/actionlint.tar.gz" | sha256sum --check -
tar -xzf "$lint_dir/actionlint.tar.gz" -C "$lint_dir" actionlint
"$lint_dir/actionlint" -shellcheck='' -pyflakes='' \
  "$repo_dir/.github/workflows/axelor-full-stack.yml"
