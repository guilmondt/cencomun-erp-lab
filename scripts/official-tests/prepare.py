"""Create an upstream-only test site; never reset or reuse an unmarked site."""

import argparse
import json
import secrets
import subprocess
from pathlib import Path

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
CLI = str(ROOT / 'bench-tools/bin/bench')


def main(app):
    site = 'ccm-upstream-' + app + '.test'
    private_dir = ROOT / 'official-tests'
    private_dir.mkdir(mode=0o700, exist_ok=True)
    marker = private_dir / (app + '-isolated-created.json')
    private = private_dir / (app + '-private.json')
    if not private.exists():
        private.write_text(json.dumps({'admin_password': secrets.token_urlsafe(32)}))
        private.chmod(0o600)
    credentials = json.loads(private.read_text())
    bootstrap = json.loads((ROOT / 'secrets.json').read_text())

    def run(label, args):
        with (private_dir / (app + '-' + label + '.log')).open('w') as log:
            result = subprocess.run([CLI, *args], cwd=BENCH, stdout=log, stderr=subprocess.STDOUT)
        print(app, label, 'exit', result.returncode, flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)

    if not marker.exists():
        if (BENCH / 'sites' / site).exists():
            raise SystemExit('Unmarked existing official site: inspect; never drop/force it.')
        run('new-site', ['new-site', site, '--db-name', 'ccm_upstream_' + app,
            '--db-host', '127.0.0.1', '--db-port', '3307', '--db-socket', str(ROOT / 'mariadb.sock'),
            '--db-root-username', 'ccm_bootstrap', '--db-root-password', bootstrap['bootstrap_password'],
            '--admin-password', credentials['admin_password']])
        marker.write_text(json.dumps({'site': site, 'initial_state': 'new empty Frappe site',
            'allowed_apps': ['frappe'] + (['erpnext'] if app == 'erpnext' else [])}))
    if app == 'erpnext':
        run('install', ['--site', site, 'install-app', 'erpnext'])
    # These site-local switches are the official Frappe CI test preparation.
    # Server Script remains disabled on Cencomun/baseline/recovery sites.
    for key, value in [('allow_tests', '1'), ('server_script_enabled', '1')]:
        run('config-' + key, ['--site', site, 'set-config', key, value, '--parse'])
    # Official command tests spawn new sites and read this value from conf.
    # Root login/password live only in the isolated Bench's private config.
    run('config-admin', ['--site', site, 'set-config', 'admin_password', credentials['admin_password']])
    # The suite gets its own official `bench --site ... serve` process; the
    # baseline/Core web server and its default site never change.
    port = 8002 if app == 'frappe' else 8005
    run('config-host', ['--site', site, 'set-config', 'host_name', f'http://127.0.0.1:{port}'])
    config = {'auto_email_id': 'test@example.com', 'mail_server': 'localhost',
              'mail_port': 2525, 'mail_login': 'test@example.com', 'mail_password': 'test',
              'disable_mail_smtp_authentication': 1}
    for key, value in config.items():
        run('config-' + key, ['--site', site, 'set-config', key, str(value),
                             *(['--parse'] if isinstance(value, int) else [])])
    if app == 'erpnext':
        # Exactly the bootstrap module used by pinned ERPNext CI. Zero tests here
        # are fixture preparation only, never evidence of a passing suite.
        run('bootstrap', ['--site', site, 'run-tests', '--lightmode', '--module',
                          'erpnext.tests.bootstrap_test_data'])
    else:
        # Official hook before unit tests avoids the pinned runner's request=None
        # setup-wizard failure between categories. The hook still runs normally
        # inside the suite; nothing is skipped or monkeypatched.
        run('bootstrap', ['--site', site, 'execute', 'frappe.utils.install.before_tests'])
    print('Prepared official-only site:', site, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    main(parser.parse_args().app)
