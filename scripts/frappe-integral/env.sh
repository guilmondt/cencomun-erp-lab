#!/usr/bin/env bash
# Source this file; credentials are generated locally and never exported here.
export CCM_FRAPPE_ROOT=/workspace/.local/frappe-integral
export UV_CACHE_DIR=/workspace/.cache/uv
export UV_PYTHON_INSTALL_DIR=/workspace/.tools/python
export UV_PYTHON_BIN_DIR=/workspace/.tools/bin
export PIP_CACHE_DIR=/workspace/.cache/pip
export XDG_CACHE_HOME=/workspace/.cache
export XDG_CONFIG_HOME=/workspace/.config
export YARN_CACHE_FOLDER=/workspace/.cache/yarn
export npm_config_cache=/workspace/.cache/npm
export FRAPPE_SOCKETIO_UDS="$CCM_FRAPPE_ROOT/socketio.sock"
export PATH="$CCM_FRAPPE_ROOT/sysroot/usr/bin:$CCM_FRAPPE_ROOT/sysroot/usr/sbin:$CCM_FRAPPE_ROOT/bench-tools/bin:$CCM_FRAPPE_ROOT/node-tools/node_modules/.bin:/workspace/.tools/python/cpython-3.14.0-linux-x86_64-gnu/bin:$PATH"
export LD_LIBRARY_PATH="$CCM_FRAPPE_ROOT/sysroot/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export MYSQLCLIENT_CFLAGS="-I$CCM_FRAPPE_ROOT/sysroot/usr/include/mariadb"
export MYSQLCLIENT_LDFLAGS="-L$CCM_FRAPPE_ROOT/sysroot/usr/lib/x86_64-linux-gnu -lmariadb"
