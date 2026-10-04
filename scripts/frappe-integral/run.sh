#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_dir/scripts/frappe-integral/env.sh"
cd "$repo_dir"
runtime_python="$CCM_FRAPPE_ROOT/bench/env/bin/python"
python scripts/frappe-integral/services.py start
"$runtime_python" - <<'PY'
import importlib.util
from pathlib import Path
p = Path('scripts/frappe-integral/validate_restart.py')
spec = importlib.util.spec_from_file_location('readiness', p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.wait_ready()
PY
"$runtime_python" scripts/frappe-integral/bootstrap_validation.py
"$runtime_python" scripts/frappe-integral/validate_http.py before
"$runtime_python" scripts/frappe-integral/validate_infrastructure.py before
"$runtime_python" scripts/frappe-integral/validate_restart.py
"$runtime_python" -m unittest discover -s labs/frappe/tests -v
git -C "$CCM_FRAPPE_ROOT/bench/apps/frappe" diff --exit-code
git -C "$CCM_FRAPPE_ROOT/bench/apps/erpnext" diff --exit-code
./scripts/verify-repo.sh
git diff --check
"$runtime_python" scripts/frappe-integral/publish_evidence.py
