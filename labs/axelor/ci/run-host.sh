#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$repo_dir"
source labs/axelor/ci/pins.sh
docker info > /dev/null
state_dir=$(mktemp -d "${RUNNER_TEMP:-/tmp}/ccm-axelor-ci.XXXXXX")
results_dir=${CCM_CI_RESULTS:-"$state_dir/results"}
mkdir -p "$state_dir/private" "$state_dir/results" "$state_dir/runtime"
chmod 700 "$state_dir/private"
prefix="ccm-axelor-${GITHUB_RUN_ID:-local}-$$"
cleanup() {
  status=$?
  trap - EXIT
  docker logs "$prefix-db" > "$state_dir/private/postgres.log" 2>&1 || true
  docker logs "$prefix-app" > "$state_dir/private/container.log" 2>&1 || true
  docker rm --force --volumes "$prefix-app" "$prefix-db" > /dev/null 2>&1 || true
  docker network rm "$prefix" > /dev/null 2>&1 || true
  python3 - "$state_dir" "$results_dir" "$status" <<'PY'
import json,shutil,sys
from pathlib import Path
state,target=map(Path,sys.argv[1:3]); target.mkdir(parents=True,exist_ok=True)
password=(state/'private/postgres.env').read_text().split('POSTGRES_PASSWORD=',1)[1].splitlines()[0]
for p in [state/'private/postgres.log', state/'private/container.log']:
    (state/'results'/p.name).write_text(p.read_text(errors='replace').replace(password,'[REDACTED]'))
(state/'results/exit-status.json').write_text(json.dumps({'exit_status':int(sys.argv[3])})+'\n')
if target.resolve() != (state/'results').resolve():
    shutil.copytree(state/'results',target,dirs_exist_ok=True)
print('Runner exit status:',sys.argv[3])
print('Sanitized evidence directory:',target)
if int(sys.argv[3]):
    candidates=[target/name for name in ['app-restart.log','app-first.log','frozen-build.log','full-build.log','init-scope.log','module-tests.log','setup.log']]
    log=next((p for p in candidates if p.exists() and p.stat().st_size),None)
    detail='\n'.join(log.read_text(errors='replace').splitlines()[-80:]) if log else 'No runner log available'
    if (target/'container.log').exists():
        detail+='\nContainer summary:\n'+'\n'.join((target/'container.log').read_text(errors='replace').splitlines()[-25:])
    detail=detail[-50000:].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
    print('::error title=Axelor full-stack failure::'+detail)
else:
    evidence={name:json.loads((target/name).read_text()) for name in ['upstream-tests.json','smoke-first.json','smoke-restart.json']}
    evidence['postgres']=(target/'postgres-version.txt').read_text().strip()
    evidence['lab_commit']=(target/'lab-commit.txt').read_text().strip()
    evidence['war_sha256']=(target/'war-sha256.txt').read_text().strip().split()[0]
    print('::notice title=Axelor full-stack evidence::'+json.dumps(evidence))
PY
  exit "$status"
}
# Generated test credential, used only by our disposable PostgreSQL container.
python3 - "$state_dir/private/postgres.env" <<'PY'
import secrets,sys
from pathlib import Path
p=Path(sys.argv[1]); p.write_text('POSTGRES_DB=ccm_axelor_ci\nPOSTGRES_USER=ccm_ci\nPOSTGRES_PASSWORD='+secrets.token_hex(32)+'\n'); p.chmod(0o600)
PY
trap cleanup EXIT
docker pull "$CCM_BUILD_IMAGE"
docker pull "$CCM_POSTGRES_IMAGE"
docker image inspect "$CCM_BUILD_IMAGE" "$CCM_POSTGRES_IMAGE" \
  --format '{{json .RepoDigests}}' > "$state_dir/results/image-digests.jsonl"
git rev-parse HEAD > "$state_dir/results/lab-commit.txt"
cp labs/axelor/ci/pins.sh "$state_dir/results/runtime-pins.sh"
docker network create "$prefix" > /dev/null
docker run --detach --name "$prefix-db" --network "$prefix" --network-alias postgres \
  --env-file "$state_dir/private/postgres.env" "$CCM_POSTGRES_IMAGE" > /dev/null
ready=0
for attempt in {1..30}; do
  if docker exec "$prefix-db" pg_isready -U ccm_ci -d ccm_axelor_ci > /dev/null 2>&1; then
    ready=1; break
  fi
  sleep 2
done
test "$ready" = 1
docker exec "$prefix-db" psql -U ccm_ci -d ccm_axelor_ci -Atc 'SHOW server_version;' \
  > "$state_dir/results/postgres-version.txt"
# No token, SSH key or production variable is forwarded into this container.
docker run --name "$prefix-app" --network "$prefix" \
  --volume "$repo_dir:/workspace/cencomun-erp-lab" \
  --volume "$state_dir:/workspace/ccm-ci-state" \
  --env CCM_CI_STATE=/workspace/ccm-ci-state \
  --env CCM_AXELOR_RUNTIME=/workspace/ccm-ci-state/runtime \
  --workdir /workspace/cencomun-erp-lab \
  "$CCM_BUILD_IMAGE" bash labs/axelor/ci/bootstrap.sh
