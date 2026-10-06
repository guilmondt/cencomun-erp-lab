#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_dir/scripts/frappe-integral/env.sh"
export PATH="$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
cd "$repo_dir"
"$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/core-test/run.py
