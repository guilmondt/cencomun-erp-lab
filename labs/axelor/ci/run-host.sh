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
    if (target/'core-test/coverage.json').exists():
        core=json.loads((target/'core-test/coverage.json').read_text())
        print('::warning title=Core native coverage::'+json.dumps({'groups':core['counts'],'coverage_revision':core['coverage_revision']}))
    candidates=[target/name for name in ['app-restart.log','app-first.log','frozen-build.log','full-build.log','init-scope.log','module-tests.log','setup.log','evidence-tests.log']]
    log=next((p for p in candidates if p.exists() and p.stat().st_size),None)
    # GitHub truncates annotation messages around 4 KiB. Keep the client error
    # first, plus the failing-stage tail, rather than losing the exception.
    detail=''
    if (target/'container.log').exists():
        detail='Container tail:\n'+'\n'.join((target/'container.log').read_text(errors='replace').splitlines()[-12:])[-2200:]
    detail+='\nFailing stage:\n'+ ('\n'.join(log.read_text(errors='replace').splitlines()[-30:])[-1400:] if log else 'No runner log available')
    detail=detail.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
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
  "$CCM_BUILD_IMAGE" bash labs/axelor/ci/bootstrap.sh &
app_runner_pid=$!
# Supervise only our disposable containers. The build container has no Docker
# socket; native service recovery requests a DB restart through a private marker.
while kill -0 "$app_runner_pid" 2>/dev/null; do
  if test -f "$state_dir/private/baseline-backup.request" && ! test -f "$state_dir/private/baseline-backup.done"; then
    docker exec "$prefix-db" pg_dump -U ccm_ci -d ccm_axelor_ci -Fc > "$state_dir/private/baseline.dump"
    sha256sum "$state_dir/private/baseline.dump" | cut -d ' ' -f 1 > "$state_dir/results/baseline-backup.sha256"
    touch "$state_dir/private/baseline-backup.done"
  fi
  if test -f "$state_dir/private/isolated-restore.request" && ! test -f "$state_dir/private/isolated-restore.done"; then
    docker exec "$prefix-db" createdb -U ccm_ci ccm_axelor_replay
    docker exec -i "$prefix-db" pg_restore -U ccm_ci -d ccm_axelor_replay --exit-on-error < "$state_dir/private/baseline.dump"
    python3 - "$state_dir" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);receipt={'source_database':'ccm_axelor_ci','target_database':'ccm_axelor_replay','backup_sha256':(root/'results/baseline-backup.sha256').read_text().strip(),'restore_exit_code':0,'scope':'Fresh disposable database; same frozen baseline; no upgrade'}
(root/'results/isolated-restore.json').write_text(json.dumps(receipt)+'\n')
print('::notice title=Core isolated database restore::'+json.dumps(receipt),flush=True)
PY
    touch "$state_dir/private/isolated-restore.done"
  fi
  for recovery_phase in primary repeat; do
  if test -f "$state_dir/private/restart-db-$recovery_phase.request" && ! test -f "$state_dir/private/restart-db-$recovery_phase.done"; then
    docker exec "$prefix-db" psql -U ccm_ci -d ccm_axelor_ci -Atc 'SELECT pg_postmaster_start_time();' > "$state_dir/private/postgres-before.txt"
    docker restart "$prefix-db" > /dev/null
    pg_ready=0
    for pg_attempt in {1..30}; do
      if docker exec "$prefix-db" pg_isready -U ccm_ci -d ccm_axelor_ci > /dev/null 2>&1; then pg_ready=1; break; fi
      sleep 2
    done
    test "$pg_ready" = 1
    docker exec "$prefix-db" psql -U ccm_ci -d ccm_axelor_ci -Atc 'SELECT pg_postmaster_start_time();' > "$state_dir/private/postgres-after.txt"
    python3 - "$state_dir" "$recovery_phase" <<'PY'
import json,sys
from pathlib import Path
state=Path(sys.argv[1]);before=(state/'private/postgres-before.txt').read_text().strip();after=(state/'private/postgres-after.txt').read_text().strip()
assert before and after and before!=after,'PostgreSQL was not restarted'
phase=sys.argv[2]
(state/'results'/('postgres-restart-'+phase+'.json')).write_text(json.dumps({'postgres_before':before,'postgres_after':after,'postgres_restart_status':'PASS','scope':'Owned disposable CI database only','phase':phase})+'\n')
(state/'private'/('restart-db-'+phase+'.done')).touch()
PY
  fi
  done
  sleep 2
done
wait "$app_runner_pid"
