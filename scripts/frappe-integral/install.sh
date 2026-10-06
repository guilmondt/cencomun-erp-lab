#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_dir/scripts/frappe-integral/env.sh"
lock_dir="$repo_dir/labs/frappe/integral"
mkdir -p "$CCM_FRAPPE_ROOT" /workspace/.tools/bin
uv python install 3.14.0
python -c 'import sys; assert sys.version_info[:3] == (3, 14, 0)'
test "$(node --version)" = v24.19.0
python "$repo_dir/scripts/frappe-integral/system_packages.py"
python "$repo_dir/scripts/frappe-integral/prepare_runtime.py"

if [[ ! -x "$CCM_FRAPPE_ROOT/bench-tools/bin/bench" ]]; then
  uv venv "$CCM_FRAPPE_ROOT/bench-tools" --python /workspace/.tools/python/cpython-3.14.0-linux-x86_64-gnu/bin/python3.14
fi
uv pip install --python "$CCM_FRAPPE_ROOT/bench-tools/bin/python" -r "$lock_dir/bench-tools.lock"
mkdir -p "$CCM_FRAPPE_ROOT/node-tools"
cp "$lock_dir/node-tools.package.json" "$CCM_FRAPPE_ROOT/node-tools/package.json"
cp "$lock_dir/node-tools.package-lock.json" "$CCM_FRAPPE_ROOT/node-tools/package-lock.json"
npm ci --prefix "$CCM_FRAPPE_ROOT/node-tools" --no-audit --no-fund
export UV_CONSTRAINT="$lock_dir/python-runtime.lock"
export UV_BUILD_CONSTRAINT="$lock_dir/python-runtime.lock"
if [[ ! -x "$CCM_FRAPPE_ROOT/bench/env/bin/python" ]]; then
  cd "$CCM_FRAPPE_ROOT"
  bench init bench --frappe-branch v16.36.1 \
    --python /workspace/.tools/python/cpython-3.14.0-linux-x86_64-gnu/bin/python3.14 \
    --skip-assets --no-backups
fi
cd "$CCM_FRAPPE_ROOT/bench"
test "$(git -C apps/frappe rev-parse HEAD)" = 97a5dd93ca5883bcc9c4ef9834120c5cba397b67
if [[ ! -d apps/erpnext ]]; then
  # Skip ERPNext's recursive Yarn hook, which rewrites its tracked banking lock.
  YARN_IGNORE_SCRIPTS=true bench get-app --branch v16.36.1 --skip-assets \
    erpnext https://github.com/frappe/erpnext
fi
test "$(git -C apps/erpnext rev-parse HEAD)" = fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba
uv pip install --python env/bin/python -r "$lock_dir/python-runtime.lock"
if ! ./env/bin/python -c 'import MySQLdb' >/dev/null 2>&1; then
  # A cached native wheel may have been built before the client shared library existed.
  uv pip install --python env/bin/python --reinstall-package mysqlclient \
    --no-cache --no-binary mysqlclient mysqlclient==2.2.7
fi
./env/bin/python -c 'import MySQLdb; print("Pinned MariaDB client import passed")'
uv pip install --python env/bin/python --no-deps --no-build-isolation -e "$repo_dir/labs/frappe/cencomun_erp"
if [[ ! -e apps/cencomun_erp ]]; then
  ln -s "$repo_dir/labs/frappe/cencomun_erp" apps/cencomun_erp
fi
test "$(readlink -f apps/cencomun_erp)" = "$repo_dir/labs/frappe/cencomun_erp"
python - <<'PY'
from pathlib import Path
p = Path('sites/apps.txt')
apps = p.read_text().splitlines()
if 'cencomun_erp' not in apps:
    apps.append('cencomun_erp')
p.write_text('\n'.join(apps) + '\n')
PY
yarn --cwd apps/frappe install --frozen-lockfile
YARN_IGNORE_SCRIPTS=true yarn --cwd apps/erpnext install --frozen-lockfile
mkdir -p "$CCM_FRAPPE_ROOT/banking-dependencies"
cp apps/erpnext/banking/package.json "$CCM_FRAPPE_ROOT/banking-dependencies/package.json"
cp "$lock_dir/erpnext-banking.yarn.lock" "$CCM_FRAPPE_ROOT/banking-dependencies/yarn.lock"
yarn --cwd "$CCM_FRAPPE_ROOT/banking-dependencies" install --frozen-lockfile
if [[ ! -e apps/erpnext/banking/node_modules ]]; then
  ln -s "$CCM_FRAPPE_ROOT/banking-dependencies/node_modules" apps/erpnext/banking/node_modules
fi
test "$(readlink -f apps/erpnext/banking/node_modules)" = "$CCM_FRAPPE_ROOT/banking-dependencies/node_modules"
git -C apps/frappe diff --exit-code
git -C apps/erpnext diff --exit-code
python "$repo_dir/scripts/frappe-integral/services.py" start mariadb redis_cache redis_queue
python "$repo_dir/scripts/frappe-integral/create_site.py"
bench --site ccm-frappe.test install-app erpnext
bench --site ccm-frappe.test install-app cencomun_erp
bench build
./env/bin/python "$repo_dir/scripts/frappe-integral/bootstrap_validation.py"
git -C apps/frappe diff --exit-code
git -C apps/erpnext diff --exit-code
echo 'Real-site setup complete; run the integral validation to prove behavior.'
