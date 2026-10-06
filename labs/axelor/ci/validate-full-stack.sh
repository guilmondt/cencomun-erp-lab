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
echo '::notice title=Axelor module tests::2 original baseline tests and 7 Core policy unit tests passed; compilation, JAR metadata and source checks passed.'
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
  :war :generateRunner :modules:axelor-base:test \
  --tests com.axelor.apps.base.service.partner.registrationnumber.TestTaxNumberHelper \
  --write-locks > "$state_dir/private/full-build.log" 2>&1
python3 - "$host_dir" "$results_dir" <<'PY'
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
host,results=map(Path,sys.argv[1:])
path=host/'modules/axelor-open-suite/axelor-base/build/test-results/test/TEST-com.axelor.apps.base.service.partner.registrationnumber.TestTaxNumberHelper.xml'
suite=ET.parse(path).getroot()
assert int(suite.attrib['tests']) == 16, suite.attrib
assert all(int(suite.attrib[k]) == 0 for k in ['errors','failures','skipped']), suite.attrib
(results/'upstream-tests.json').write_text(json.dumps(suite.attrib,indent=2)+'\n')
print('Upstream representative suite: 16 tests passed, no failures/errors/skips')
path=Path('/workspace/cencomun-erp-lab/labs/axelor/cencomun-baseline/build/full/test-results/test/TEST-com.cencomun.core.NativeAddressTemplateTest.xml')
suite=ET.parse(path).getroot()
assert int(suite.attrib['tests']) == 8, suite.attrib
assert all(int(suite.attrib[k]) == 0 for k in ['errors','failures','skipped']), suite.attrib
(results/'native-fixture-tests.json').write_text(json.dumps(suite.attrib,indent=2)+'\n')
print('Native address callback regression: 8 cases passed, no failures/errors/skips; no database coverage claim')
for name,count in [('NativePermissionFilterTest',5),('NativeInvoiceRuntimeTest',2)]:
    path=Path('/workspace/cencomun-erp-lab/labs/axelor/cencomun-baseline/build/full/test-results/test')/f'TEST-com.cencomun.core.{name}.xml'
    suite=ET.parse(path).getroot()
    assert int(suite.attrib['tests']) == count, suite.attrib
    assert all(int(suite.attrib[k]) == 0 for k in ['errors','failures','skipped']), suite.attrib
    (results/f'{name}.json').write_text(json.dumps(suite.attrib,indent=2)+'\n')
    print(f'{name}: {count} native unit cases passed; DB acceptance requires Core execution')
PY
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
echo 'Phase: CO00 then TAX01-W, native Core gates and strict coverage publication'
python3 /workspace/cencomun-erp-lab/labs/axelor/core-test/run.py \
  --base http://127.0.0.1:8080/axelor-erp \
  --fixtures /workspace/cencomun-erp-lab/fixtures/ccm-core-v1 \
  --output "$results_dir/core-test" || core_status=$?
stop_app
echo 'Phase: server restart against the same disposable database'
start_app restart
python3 /workspace/cencomun-erp-lab/labs/axelor/ci/smoke.py \
  http://127.0.0.1:8080/axelor-erp "$results_dir/smoke-restart.json" 900
stop_app
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
