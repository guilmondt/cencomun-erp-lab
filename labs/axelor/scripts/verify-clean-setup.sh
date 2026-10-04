#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
source_commit=$(git -C "$repo_dir" rev-parse --verify 'HEAD^{commit}')
repro_dir=$(mktemp -d /tmp/ccm-axelor-clean-setup.XXXXXX)
printf 'Clean setup evidence: %s\nSource commit: %s\n' "$repro_dir" "$source_commit"

# Regression coverage for the first wrapper download: the normal workflow can
# hide bootstrap/proxy defects when GRADLE_USER_HOME already has a distribution.
# Use committed source, an independent checkout and no existing runtime/cache.
git clone --no-hardlinks --no-checkout "$repo_dir" "$repro_dir/repo" \
  > "$repro_dir/checkout.log" 2>&1
git -C "$repro_dir/repo" checkout --detach "$source_commit" \
  >> "$repro_dir/checkout.log" 2>&1
export CCM_AXELOR_RUNTIME="$repro_dir/runtime"
test ! -e "$CCM_AXELOR_RUNTIME"
if ! bash "$repro_dir/repo/labs/axelor/scripts/setup-cloud.sh" > "$repro_dir/setup.log" 2>&1; then
  printf 'Clean installation failed; inspect %s/setup.log\n' "$repro_dir" >&2
  exit 1
fi
if ! bash "$repro_dir/repo/labs/axelor/scripts/validate.sh" > "$repro_dir/validation.log" 2>&1; then
  printf 'Clean validation failed; inspect %s/validation.log\n' "$repro_dir" >&2
  exit 1
fi
test -z "$(git -C "$repro_dir/repo" status --porcelain)"
printf 'Clean setup passed: exact committed source, empty dependency directory, verified wrapper, compilation/JAR and 2 tests.\n'
