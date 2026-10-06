"""Prepare Payments CI fixtures without shadowing the official `payments` package."""

import importlib.metadata
import json
import subprocess
from pathlib import Path

from run import SuiteLock, active_runners, ROOT, BENCH, REPO
from worker import STATE, birth

LOCK = REPO / 'labs/frappe/integral/official-payments.lock.json'
SOURCE = ROOT / 'official-fixtures/payments'
MARKER = ROOT / 'official-tests/payments-prepared.json'


def distributions():
    output = subprocess.check_output([str(BENCH / 'env/bin/python'), '-c',
        'import importlib.metadata,json; print(json.dumps({d.metadata["Name"].lower().replace("_","-"):d.version for d in importlib.metadata.distributions()}))'], text=True)
    return json.loads(output)


def main():
    with SuiteLock():
        if active_runners():
            raise RuntimeError('An official runner is active; do not modify its dependencies.')
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        if state and birth(state['pid']) == state['birth']:
            raise RuntimeError('Stop the official worker before dependency preparation.')
        lock = json.loads(LOCK.read_text())
        if not SOURCE.exists():
            SOURCE.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'clone', '--no-checkout', lock['repository'], str(SOURCE)], check=True)
            subprocess.run(['git', 'checkout', '--detach', lock['sha']], cwd=SOURCE, check=True)
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
        changes = subprocess.check_output(['git', 'status', '--porcelain'], cwd=SOURCE, text=True).strip()
        if actual != lock['sha'] or changes:
            raise RuntimeError('Payments fixture clone must be clean at its exact locked SHA.')
        target = BENCH / 'apps/payments'
        if not target.exists():
            subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(SOURCE), str(target)], check=True)
            subprocess.run(['git', 'checkout', '--detach', lock['sha']], cwd=target, check=True)
        elif subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=target, text=True).strip() != lock['sha']:
            raise RuntimeError('Existing copied Payments checkout has a different SHA; preserve and inspect it.')
        before = distributions()
        # The two legacy source SDKs need setuptools to build their wheel.
        # Install its already-hashed exact pin first, with no build isolation or
        # floating build dependencies; the remaining lock then uses this venv.
        setuptools = next(p for p in lock['packages'] if p['name'] == 'setuptools')
        bootstrap_lock = ROOT / 'official-tests/payments-build-bootstrap.lock'
        bootstrap_lock.write_text('setuptools==' + setuptools['version'] +
                                  ' --hash=sha256:' + setuptools['sha256'] + '\n')
        private = ROOT / 'official-tests/payments-install.log'
        with private.open('a') as log:
            for args in [
                ['--no-deps', '--require-hashes', '-r', str(bootstrap_lock)],
                ['--no-deps', '--no-build-isolation', '--require-hashes', '-r',
                 str(REPO / 'labs/frappe/integral/official-payments.lock.txt')],
                ['--no-deps', '--no-build-isolation', '-e', str(target)],
            ]:
                result = subprocess.run([str(BENCH / 'env/bin/python'), '-m', 'pip', 'install', *args],
                                        stdout=log, stderr=subprocess.STDOUT)
                if result.returncode:
                    raise RuntimeError('Payments preparation failed; inspect its private install log.')
        after = distributions()
        changed = {name: (version, after.get(name)) for name, version in before.items()
                   if after.get(name) != version}
        if changed:
            raise RuntimeError('Existing copied environment versions changed: ' + repr(changed))
        apps = BENCH / 'sites/apps.txt'
        names = apps.read_text().splitlines()
        if 'payments' not in names:
            apps.write_text('\n'.join([*names, 'payments']) + '\n')
        data = {'scope': lock['scope'], 'sha': actual, 'version': lock['version'],
                'source': str(SOURCE), 'installed_only_in': str(BENCH),
                'existing_package_versions_changed': changed, 'status': 'PASS',
                'added_packages': {name: version for name, version in after.items() if name not in before},
                'lock': str(LOCK.relative_to(REPO))}
        MARKER.write_text(json.dumps(data, indent=2) + '\n')
        (REPO / 'reports/evidence/frappe-official/payments-preparation.json').write_text(json.dumps(data, indent=2) + '\n')
        print('PASS: pinned Payments CI fixture; existing package versions unchanged.')


if __name__ == '__main__':
    main()
