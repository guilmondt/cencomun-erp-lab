# Issue #1 — Codex Cloud environment preflight

Completed before beginning Issue #2 on 2026-10-04.

Repository: `guilmondt/cencomun-erp-lab`; working branch: `lab/frappe-baseline`.
HEAD: `33c413764de947b9e6610318ccc673ec6ac0150f` (matches remote branch).
Requested environment name: `ccm-erp-lab-frappe`; naming is managed in environment settings and cannot be inspected through available tools.
OS: Debian GNU/Linux 13.6, Linux x86_64. Reported resources: 5 CPUs, 33 GiB RAM, 30 GiB available disk. These are runtime observations, not guaranteed future allocations.

## Checks and reproducibility

Read `AGENTS.md`, `versions.lock`, `docs/PROJECT_CHARTER.md`, `docs/COMPARISON_PROTOCOL.md`, and `docs/CODEX_CLOUD_SETUP.md`.

- `./scripts/preflight.sh`: passed; an inventory check, not an ERP readiness check.
- `./scripts/verify-repo.sh`: passed.
- `bash -n scripts/preflight.sh scripts/verify-repo.sh`: passed.
- Native Git HTTPS reads of origin and `lab/frappe-baseline`: passed.
- GitHub API reads of Issues #1 and #2: passed after `api.github.com` was added and saved in environment settings. Initial HTTP 403 network block resolved.
- Python 3.14.0 imports of `ssl`, `sqlite3`, `venv`, `tomllib` and TOML version-pin parsing: passed.
- Installation repeated successfully with `uv python install 3.14.0`; exact Python version retained.
- Saved setup/start instructions and Python installation are present after environment reconnection. The initial setup script is saved in the active configuration; this is not an independent new-task restoration test.

Activate the runtime before running Python commands:

```sh
export UV_CACHE_DIR=/workspace/.cache/uv
export UV_PYTHON_INSTALL_DIR=/workspace/.tools/python
export UV_PYTHON_BIN_DIR=/workspace/.tools/bin
export PATH=/workspace/.tools/python/cpython-3.14.0-linux-x86_64-gnu/bin:$PATH
cd /workspace/cencomun-erp-lab
uv python install 3.14.0
./scripts/preflight.sh
./scripts/verify-repo.sh
```

## Explicit limitations

- Network remains restricted with the package-manager preset and custom domain `api.github.com`.
- No production secrets are required or added; no secret values were printed.
- Version pins and existing tracked files are unchanged at completion of Issue #1.
- Initial Git status was clean; at this check only the untracked `reports/` output exists.
- Bench, Yarn, MariaDB 11.8 and Redis are absent. No Frappe app or platform tests existed before Issue #2. Build tools for the custom app will be prepared in Issue #2.
- Java runtime exists but javac and Gradle are absent; Axelor is outside this environment's scope.
- Docker CLI presence does not prove Docker-in-Docker works. The setup does not depend on it.
- Full ERP/database/service validation belongs in CI or a dedicated runner, per repository policy. No ERP behavior, migrations or Core Test parity is claimed.
- GitHub issue state has not been changed; this report records local acceptance evidence.

## Exact runtime inventory and pins

```text
== Cencomun ERP Lab preflight ==
date_utc=2026-10-04T13:33:40Z
pwd=/workspace/cencomun-erp-lab
os=Linux
arch=x86_64

-- resources --
cpus=5
               total        used        free      shared  buff/cache   available
Mem:            33Gi       704Mi        32Gi       2.5Mi        43Mi        32Gi
Swap:             0B          0B          0B
Filesystem      Size  Used Avail Use% Mounted on
overlay          32G  772K   30G   1% /workspace

-- tools --
git        git version 2.52.0
python3    Python 3.14.0
python     Python 3.14.0
node       v24.19.0
npm        11.9.0
pnpm       11.19.0
yarn       MISSING
java       openjdk 21.0.12.1 2026-08-18
javac      MISSING
gradle     MISSING
docker     Docker version 28.4.0, build d8eb465
podman     MISSING

-- git --
## lab/frappe-baseline
?? reports/

-- pins --
# Pinned research baselines — 2026-10-04

[frappe]
framework_family = "16"
framework_reference = "v16.36.1"
erpnext_reference = "v16.36.1"
database = "MariaDB 11.8"
python_min = "3.14"
node_min = "24"

[axelor]
aos_reference = "v9.1.8"
aop_family = "8.2"
java = "21"
database = "PostgreSQL >= 12"

[policy]
allow_floating_upstream_branches = false
allow_latest_tags = false
```
