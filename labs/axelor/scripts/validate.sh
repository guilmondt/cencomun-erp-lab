#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
module_dir="$repo_dir/labs/axelor/cencomun-baseline"
runtime_dir=${CCM_AXELOR_RUNTIME:-/workspace/ccm-axelor-runtime}
cd "$repo_dir"

# Force the two module tests to execute, including on a restored build cache.
# Do not use the host's build/formatCode/spotlessApply tasks: those write source.
bash labs/axelor/scripts/gradle.sh \
  :modules:cencomun-baseline:classes \
  :modules:cencomun-baseline:test \
  :modules:cencomun-baseline:jar \
  --rerun-tasks "$@"

python3 - "$module_dir" <<'PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

module = Path(sys.argv[1])
result = module / 'build/test-results/test/TEST-com.cencomun.baseline.module.CencomunModuleTest.xml'
suite = ET.parse(result).getroot()
assert int(suite.attrib['tests']) == 2, suite.attrib
assert int(suite.attrib['failures']) == 0, suite.attrib
assert int(suite.attrib['errors']) == 0, suite.attrib
assert int(suite.attrib['skipped']) == 0, suite.attrib
assert {case.attrib['name'] for case in suite.findall('testcase')} == {
    'registersWithThePlatformInjectorWithoutADatabase()',
    'generatedMetadataIdentifiesTheCustomModule()',
}
policy_path = module / 'build/test-results/test/TEST-com.cencomun.core.MoneyPolicyTest.xml'
policy_count = 0
if policy_path.exists():
    policy = ET.parse(policy_path).getroot()
    policy_count = int(policy.attrib['tests'])
    assert policy_count == 7, policy.attrib
    assert all(int(policy.attrib[k]) == 0 for k in ['failures','errors','skipped']), policy.attrib
artifact = module / 'build/libs/cencomun-baseline-0.1.0.jar'
with zipfile.ZipFile(artifact) as jar:
    entries = set(jar.namelist())
    assert 'com/cencomun/baseline/module/CencomunModule.class' in entries
    assert 'META-INF/axelor-module.properties' in entries
    assert not any(name.startswith('com/axelor/') for name in entries)
    if policy_count:
        assert 'ccm-core-v1/manifest.json' in entries
        import hashlib
        assert hashlib.sha256(jar.read('ccm-core-v1/manifest.json')).hexdigest() == '28496929050e7cfeea214dbf0ee5cbd589a08ab2adb60e1849877778baaf9aed'
print(f'Validated: 2 baseline tests + {policy_count} Core policy unit tests passed; 0 failed/errors/skipped; custom JAR and metadata verified.')
PY

./scripts/verify-repo.sh
git diff --exit-code -- versions.lock
git -C "$runtime_dir/open-suite-webapp" diff --exit-code
git -C "$runtime_dir/open-suite-webapp" diff --cached --exit-code
git -C "$runtime_dir/open-suite-webapp/modules/axelor-open-suite" diff --exit-code
