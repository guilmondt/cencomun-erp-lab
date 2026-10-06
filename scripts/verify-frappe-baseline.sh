#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
export UV_CACHE_DIR=/workspace/.cache/uv
runtime_python=/workspace/.tools/python/cpython-3.14.0-linux-x86_64-gnu/bin/python3.14
build_env=/workspace/.venvs/ccm-frappe-build
output_dir="$repo_dir/reports/generated/frappe-baseline"

if [[ ! -x "$runtime_python" ]]; then
  echo 'Python 3.14.0 missing: run the saved environment installation script.' >&2
  exit 1
fi
mkdir -p /workspace/.venvs "$output_dir"
if [[ ! -x "$build_env/bin/python" ]]; then
  uv venv "$build_env" --python "$runtime_python"
fi
"$build_env/bin/python" -c 'import sys; assert sys.version_info[:3] == (3, 14, 0), sys.version'
uv pip install --python "$build_env/bin/python" --require-hashes \
  -r labs/frappe/requirements-build.lock
uv pip install --python "$build_env/bin/python" --no-build-isolation \
  -e labs/frappe/cencomun_erp

# Exercise the source package before building it.
env -u PYTHONPATH "$build_env/bin/python" -m unittest discover -s labs/frappe/tests -v

# The default build makes an sdist, then builds the wheel from that sdist.
rm -f "$output_dir/cencomun_erp-0.0.1-py3-none-any.whl" \
  "$output_dir/cencomun_erp-0.0.1.tar.gz"
"$build_env/bin/python" -m build --no-isolation \
  --outdir "$output_dir" labs/frappe/cencomun_erp

# Install into a disposable environment and test without the source PYTHONPATH.
wheel_env=$(mktemp -d /workspace/.venvs/ccm-frappe-wheel.XXXXXX)
trap 'rm -rf "$wheel_env"' EXIT
uv venv "$wheel_env" --python "$runtime_python"
uv pip install --python "$wheel_env/bin/python" --no-deps \
  "$output_dir/cencomun_erp-0.0.1-py3-none-any.whl"
env -u PYTHONPATH "$wheel_env/bin/python" -m unittest discover \
  -s "$repo_dir/labs/frappe/tests" -v
env -u PYTHONPATH "$wheel_env/bin/python" -c \
  'import cencomun_erp; from importlib.metadata import version; assert version("cencomun_erp") == cencomun_erp.__version__ == "0.0.1"; print("Installed wheel version verified")'
echo 'Frappe skeleton source/build/installed-wheel validation passed.'
