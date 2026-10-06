#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$repo_dir"
source labs/axelor/ci/pins.sh
export CCM_PILOT_STATE=${CCM_PILOT_STATE:-/workspace/axelor-pilot-state}
export CCM_CI_STATE="$CCM_PILOT_STATE"
export CCM_AXELOR_FULL_STACK=1
# Archive acquisition uses the existing network policy; failure must not trigger
# automatic permission or network expansion. No dependency lock is refreshed.
mkdir -p "$CCM_PILOT_STATE"/{node,yarn,locks,results}
if ! test -f "$CCM_PILOT_STATE/node.tar.xz"; then
  curl --fail --location --silent --show-error "https://nodejs.org/dist/v$CCM_NODE_VERSION/node-v$CCM_NODE_VERSION-linux-x64.tar.xz" -o "$CCM_PILOT_STATE/node.tar.xz"
fi
printf '%s  %s\n' "$CCM_NODE_SHA256" "$CCM_PILOT_STATE/node.tar.xz" | sha256sum --check -
if ! test -f "$CCM_PILOT_STATE/yarn.tgz"; then
  curl --fail --location --silent --show-error "https://registry.npmjs.org/yarn/-/yarn-$CCM_YARN_VERSION.tgz" -o "$CCM_PILOT_STATE/yarn.tgz"
fi
python3 - "$CCM_PILOT_STATE/yarn.tgz" "$CCM_YARN_SHA512_BASE64" <<'PY'
import base64,hashlib,sys
from pathlib import Path
assert base64.b64encode(hashlib.sha512(Path(sys.argv[1]).read_bytes()).digest()).decode()==sys.argv[2]
PY
tar -xJf "$CCM_PILOT_STATE/node.tar.xz" --strip-components=1 -C "$CCM_PILOT_STATE/node"
tar -xzf "$CCM_PILOT_STATE/yarn.tgz" --strip-components=1 -C "$CCM_PILOT_STATE/yarn"
cp reports/evidence/axelor-core/runs/37469716840/locks/*.lockfile "$CCM_PILOT_STATE/locks/"
export PATH="$CCM_PILOT_STATE/node/bin:$CCM_PILOT_STATE/yarn/bin:$PATH"
export npm_config_cache="$CCM_PILOT_STATE/npm-cache"
export YARN_CACHE_FOLDER="$CCM_PILOT_STATE/yarn-cache"
bash labs/axelor/scripts/gradle.sh \
  --init-script "$repo_dir/labs/axelor/ci/full-stack.init.gradle" \
  --init-script "$repo_dir/labs/axelor/pilot/frontend.init.gradle" \
  :modules:cencomun-baseline:test :war :generateRunner "$@"
