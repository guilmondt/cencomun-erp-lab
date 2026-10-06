#!/usr/bin/env bash
set -euo pipefail
cd /workspace/cencomun-erp-lab
source labs/axelor/ci/pins.sh
state_dir=${CCM_CI_STATE:?}
runtime_dir=${CCM_AXELOR_RUNTIME:?}
results_dir="$state_dir/results"
mkdir -p "$state_dir/private" "$state_dir/locks" "$runtime_dir"
umask 077
app_pid=''
core_status=0
stop_app() {
  if test -n "$app_pid"; then
    kill -TERM "$app_pid" 2>/dev/null || true
    wait "$app_pid" 2>/dev/null || true
    app_pid=''
  fi
}
finish() {
  status=$?
  trap - EXIT
  stop_app
  python3 - "$state_dir" <<'PY'
from pathlib import Path
import sys
state=Path(sys.argv[1])
password=(state/'private/postgres.env').read_text().split('POSTGRES_PASSWORD=',1)[1].splitlines()[0]
for path in (state/'private').glob('*.log'):
    (state/'results'/path.name).write_text(path.read_text(errors='replace').replace(password,'[REDACTED]'))
import shutil
if (state/'locks').exists():
    shutil.copytree(state/'locks',state/'results/locks',dirs_exist_ok=True)
for base in [Path('/workspace/cencomun-erp-lab/labs/axelor/cencomun-baseline'),
             state/'runtime/open-suite-webapp/modules/axelor-open-suite/axelor-base']:
    for report in (base/'build/test-results/test').glob('TEST-*.xml'):
        content=report.read_text(errors='replace').replace(password,'[REDACTED]')
        (state/'results'/report.name).write_text(content)
for report in Path('/workspace/cencomun-erp-lab/labs/axelor/cencomun-baseline/build/full/test-results/test').glob('TEST-*.xml'):
    (state/'results'/report.name).write_text(report.read_text(errors='replace').replace(password,'[REDACTED]'))
PY
  chmod -R a+rX "$results_dir"
  exit "$status"
}
trap finish EXIT
bash labs/axelor/ci/verify-baseline-history.sh
echo 'Phase: exact cloud baseline setup and two custom module tests'
python3 -m unittest discover -s labs/axelor/core-test -p 'test_*.py' \
  > "$state_dir/private/evidence-tests.log" 2>&1 || {
    cat "$state_dir/private/evidence-tests.log"
    exit 1
  }
bash labs/axelor/scripts/setup-cloud.sh > "$state_dir/private/setup.log" 2>&1
bash labs/axelor/scripts/validate.sh > "$state_dir/private/module-tests.log" 2>&1
echo '::notice title=Axelor module tests::22 baseline/money/order/security unit tests passed; compilation, JAR metadata and source checks passed.'
bash labs/axelor/ci/check-init-scope.sh > "$state_dir/private/init-scope.log" 2>&1
echo '::notice title=Axelor init regression::The host init script passes in an isolated buildSrc fixture without application projects.'

echo 'Phase: checksum-verified frontend runtimes'
mkdir -p "$runtime_dir/node" "$runtime_dir/yarn"
curl --fail --location --silent --show-error \
  "https://nodejs.org/dist/v$CCM_NODE_VERSION/node-v$CCM_NODE_VERSION-linux-x64.tar.xz" \
  -o "$runtime_dir/node.tar.xz"
printf '%s  %s\n' "$CCM_NODE_SHA256" "$runtime_dir/node.tar.xz" | sha256sum --check -
tar -xJf "$runtime_dir/node.tar.xz" --strip-components=1 -C "$runtime_dir/node"
curl --fail --location --silent --show-error \
  "https://registry.npmjs.org/yarn/-/yarn-$CCM_YARN_VERSION.tgz" -o "$runtime_dir/yarn.tgz"
python3 - "$runtime_dir/yarn.tgz" "$CCM_YARN_SHA512_BASE64" <<'PY'
import base64,hashlib,sys
from pathlib import Path
assert base64.b64encode(hashlib.sha512(Path(sys.argv[1]).read_bytes()).digest()).decode() == sys.argv[2]
print('Official npm Yarn integrity verified')
PY
tar -xzf "$runtime_dir/yarn.tgz" --strip-components=1 -C "$runtime_dir/yarn"
export PATH="$runtime_dir/node/bin:$runtime_dir/yarn/bin:$PATH"
test "$(node --version)" = "v$CCM_NODE_VERSION"
test "$(yarn --version)" = "$CCM_YARN_VERSION"
mkdir -p "$runtime_dir/gradle-home"
printf 'org.gradle.jvmargs=-Xmx3g -XX:MaxMetaspaceSize=1g\n' > "$runtime_dir/gradle-home/gradle.properties"
host_dir="$runtime_dir/open-suite-webapp"
cp labs/axelor/cencomun-baseline/gradle.lockfile "$state_dir/locks/cencomun-baseline.lockfile"
export CCM_AXELOR_FULL_STACK=1
init_flags=(--init-script /workspace/cencomun-erp-lab/labs/axelor/ci/full-stack.init.gradle)
echo 'Phase: full AOS compilation, frontend, WAR, embedded runner and upstream tests'
bash labs/axelor/scripts/gradle.sh "${init_flags[@]}" \
  :modules:cencomun-baseline:test --tests com.cencomun.core.NativeAddressTemplateTest \
  --tests com.cencomun.core.NativePermissionFilterTest --tests com.cencomun.core.NativeInvoiceRuntimeTest \
  --tests com.cencomun.core.NativeOrderModelTest --tests com.cencomun.core.NativeBankCsvTest --tests com.cencomun.core.NativeFinanceModelTest \
  :war :generateRunner :modules:axelor-base:test \
  --tests com.axelor.apps.base.service.partner.registrationnumber.TestTaxNumberHelper \
  --write-locks > "$state_dir/private/full-build.log" 2>&1
python3 labs/axelor/ci/validate-test-suites.py "$host_dir" \
  /workspace/cencomun-erp-lab/labs/axelor/cencomun-baseline "$results_dir"
echo '::notice title=Axelor full build::Full AOS/frontend WAR and embedded launcher compiled; 16 upstream unit cases passed.'
python3 - <<'PY'
from pathlib import Path
import zipfile
p=Path('/workspace/cencomun-erp-lab/labs/axelor/cencomun-baseline/build/full/libs/cencomun-baseline-0.1.0.jar')
with zipfile.ZipFile(p) as jar:
    entries=jar.namelist()
    assert 'com/cencomun/core/db/CcmProductProfile.class' in entries
    assert not any(n.startswith('com/axelor/') for n in entries), 'Custom artifact contains upstream classes'
print('Custom native entity compiled; artifact contains no upstream classes')
PY
echo 'Phase: replay Gradle targets with generated strict dependency locks'
bash labs/axelor/scripts/gradle.sh "${init_flags[@]}" \
  :modules:cencomun-baseline:test --tests com.cencomun.core.NativeAddressTemplateTest \
  --tests com.cencomun.core.NativePermissionFilterTest --tests com.cencomun.core.NativeInvoiceRuntimeTest \
  --tests com.cencomun.core.NativeOrderModelTest --tests com.cencomun.core.NativeBankCsvTest --tests com.cencomun.core.NativeFinanceModelTest \
  :war :generateRunner :modules:axelor-base:test \
  --tests com.axelor.apps.base.service.partner.registrationnumber.TestTaxNumberHelper \
  --offline > "$state_dir/private/frozen-build.log" 2>&1
echo '::notice title=Axelor frozen dependencies::Gradle targets replayed offline with strict generated dependency locks; no lock refresh.'

export AXELOR_CONFIG="$state_dir/private/axelor-ci.properties"
python3 - "$AXELOR_CONFIG" <<'PY'
import os,sys
from pathlib import Path
state=Path(os.environ['CCM_CI_STATE'])
env=dict(line.split('=',1) for line in (state/'private/postgres.env').read_text().splitlines())
props={
 'db.default.driver':'org.postgresql.Driver',
 'db.default.url':'jdbc:postgresql://postgres:5432/ccm_axelor_ci',
 'db.default.user':'ccm_ci','db.default.password':env['POSTGRES_PASSWORD'],
 'db.default.ddl':'update','data.import.demo-data':'false',
 'application.mode':'prod','data.upload.dir':str(state/'uploads'),
 'data.upload.temp-dir':str(state/'upload-temp'),
 'logging.path':str(state/'private/app-logs'),
 'logging.level.com.axelor':'INFO','logging.level.com.zaxxer.hikari':'WARN',
}
Path(sys.argv[1]).write_text(''.join(f'{k}={v}\n' for k,v in props.items()))
PY

java_bin="$runtime_dir/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin/java"
start_app() {
  CCM_CORE_LAB=1 "$java_bin" -Xmx3g -jar "$host_dir/build/tomcat/classpath.jar" \
    --port 8080 --options-from "$host_dir/build/tomcat/axelor-tomcat.properties" \
    > "$state_dir/private/app-$1.log" 2>&1 &
  app_pid=$!
}
cd "$host_dir"
echo 'Phase: real PostgreSQL initialization and authenticated API smoke'
start_app first
python3 /workspace/cencomun-erp-lab/labs/axelor/ci/smoke.py \
  http://127.0.0.1:8080/axelor-erp "$results_dir/smoke-first.json" 900
echo 'Phase: focused native address save, required metadata and post-commit replay'
python3 /workspace/cencomun-erp-lab/labs/axelor/ci/address-preflight.py \
  http://127.0.0.1:8080/axelor-erp "$results_dir/address-preflight.json"
request_host() {
  local operation=$1
  touch "$state_dir/private/$operation.request"
  local completed=0
  for host_attempt in {1..60}; do
    if test -f "$state_dir/private/$operation.done"; then completed=1; break; fi
    sleep 2
  done
  test "$completed" = 1
}
# This dump is private: it can contain synthetic login hashes. Never upload it.
# The snapshot precedes all Core fixtures, actors, orders and benchmark loads.
request_host baseline-backup
# Packaging only: repeat.py streams each complete original file once, plus a
# small index. Avoid duplicating phase trees in earlier per-case fragments.
export CCM_INDEXED_EVIDENCE=1
for execution_phase in primary repeat; do
  phase_output="$results_dir/core-test"
  if test "$execution_phase" = repeat; then
    phase_output="$results_dir/core-test-repeat"
    request_host isolated-restore
    python3 - "$AXELOR_CONFIG" <<'PYCONFIG'
from pathlib import Path
import sys
p=Path(sys.argv[1]);text=p.read_text();assert 'jdbc:postgresql://postgres:5432/ccm_axelor_ci' in text
p.write_text(text.replace('jdbc:postgresql://postgres:5432/ccm_axelor_ci','jdbc:postgresql://postgres:5432/ccm_axelor_replay'))
PYCONFIG
    start_app repeat
    python3 /workspace/cencomun-erp-lab/labs/axelor/ci/smoke.py \
      http://127.0.0.1:8080/axelor-erp "$results_dir/smoke-repeat.json" 900
  fi
  echo "Phase: $execution_phase all 34 groups, then frozen benchmark"
  phase_status=0
  if test "$execution_phase" = primary; then
    python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/run.py \
      --base http://127.0.0.1:8080/axelor-erp --fixtures /workspace/cencomun-erp-lab/fixtures/ccm-core-v1 --output "$phase_output" || phase_status=$?
    python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/benchmark.py \
      --base http://127.0.0.1:8080/axelor-erp --fixtures /workspace/cencomun-erp-lab/fixtures/ccm-core-v1 --output "$phase_output"
  else
    python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/run.py \
      --base http://127.0.0.1:8080/axelor-erp --fixtures /workspace/cencomun-erp-lab/fixtures/ccm-core-v1 --output "$phase_output" > "$state_dir/private/repeat-core.log" 2>&1 || phase_status=$?
    python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/benchmark.py \
      --base http://127.0.0.1:8080/axelor-erp --fixtures /workspace/cencomun-erp-lab/fixtures/ccm-core-v1 --output "$phase_output" > "$state_dir/private/repeat-benchmark.log" 2>&1
  fi
  # Recovery is independently attempted even when economic contract groups FAIL.
  app_pid_before="$app_pid"
  stop_app
  request_host "restart-db-$execution_phase"
  start_app "$execution_phase-restart"
  smoke_output="$results_dir/smoke-restart.json"
  if test "$execution_phase" = repeat; then smoke_output="$results_dir/smoke-repeat-restart.json"; fi
  python3 /workspace/cencomun-erp-lab/labs/axelor/ci/smoke.py \
    http://127.0.0.1:8080/axelor-erp "$smoke_output" 900
  python3 - "$results_dir" "$app_pid_before" "$app_pid" "$execution_phase" "$phase_output" <<'PYRESTART'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);phase=sys.argv[4];receipt=json.loads((root/('postgres-restart-'+phase+'.json')).read_text());receipt.update(app_pid_before=int(sys.argv[2]),app_pid_after=int(sys.argv[3]))
assert receipt['app_pid_before']!=receipt['app_pid_after']
(Path(sys.argv[5])/'services-restart.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Actual Core service restart:',json.dumps(receipt))
PYRESTART
  if test "$execution_phase" = primary; then
    python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/recovery_cases.py \
      --base http://127.0.0.1:8080/axelor-erp --fixtures /workspace/cencomun-erp-lab/fixtures/ccm-core-v1 --output "$phase_output" --restart-receipt "$phase_output/services-restart.json"
  else
    python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/recovery_cases.py \
      --base http://127.0.0.1:8080/axelor-erp --fixtures /workspace/cencomun-erp-lab/fixtures/ccm-core-v1 --output "$phase_output" --restart-receipt "$phase_output/services-restart.json" > "$state_dir/private/repeat-recovery.log" 2>&1
  fi
  stop_app
  python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/finalize.py /workspace/cencomun-erp-lab "$host_dir" "$phase_output" > "$state_dir/private/finalize-$execution_phase.log" 2>&1
  python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/publish_phase_evidence.py \
    "$results_dir" "$phase_output" "$smoke_output"
  if test "$phase_status" != 0; then core_status=$phase_status; fi
 done
python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/repeat.py "$results_dir" /workspace/cencomun-erp-lab/fixtures/ccm-core-v1
cd /workspace/cencomun-erp-lab
./scripts/verify-repo.sh
git diff --exit-code
git diff --cached --exit-code
git -C "$host_dir" diff --exit-code
git -C "$host_dir" diff --cached --exit-code
git -C "$host_dir/modules/axelor-open-suite" diff --exit-code
if test -f "$results_dir/core-test/coverage.json"; then
  python3 labs/axelor/core-test/finalize.py /workspace/cencomun-erp-lab \
    "$host_dir" "$results_dir/core-test"
fi
cp -r "$state_dir/locks" "$results_dir/locks"
cp labs/axelor/cencomun-baseline/build/test-results/test/TEST-*.xml "$results_dir/"
cp "$host_dir/modules/axelor-open-suite/axelor-base/build/test-results/test/TEST-"*.xml "$results_dir/"
sha256sum "$host_dir/build/libs/"*.war > "$results_dir/war-sha256.txt"
echo 'Full-stack validation completed; source and pins unchanged.'
exit "$core_status"
