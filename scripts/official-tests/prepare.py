"""Create an upstream-only test site; never reset or reuse an unmarked site."""

import argparse
import json
import secrets
import subprocess
from pathlib import Path
from run import SuiteLock, active_runners

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
CLI = str(ROOT / 'bench-tools/bin/bench')


def prepare(app, fresh=False, diagnostic=False, fixture_audit=False, official_fx_fixtures=False, fixture_order=False, final=False):
    if sum((fresh, diagnostic, fixture_audit, fixture_order, final)) > 1:
        raise ValueError('Choose one isolated site slot.')
    if (fixture_audit or fixture_order or official_fx_fixtures) and app != 'erpnext':
        raise ValueError('Official FX fixtures apply only to ERPNext.')
    suffix = '-final' if final else ('-fixture-order' if fixture_order else ('-fixture-audit' if fixture_audit else ('-diagnostic' if diagnostic else ('-fresh' if fresh else ''))))
    site = 'ccm-upstream-' + app + suffix + '.test'
    private_dir = ROOT / 'official-tests'
    private_dir.mkdir(mode=0o700, exist_ok=True)
    marker = private_dir / (app + suffix + '-isolated-created.json')
    private = private_dir / (app + suffix + '-private.json')
    if not private.exists():
        private.write_text(json.dumps({'admin_password': secrets.token_urlsafe(32)}))
        private.chmod(0o600)
    credentials = json.loads(private.read_text())
    bootstrap = json.loads((ROOT / 'secrets.json').read_text())
    payments = app == 'erpnext' and (private_dir / 'payments-prepared.json').exists()

    def run(label, args):
        logpath = private_dir / (app + suffix + '-' + label + '.log')
        attempt = 1
        while logpath.exists():
            attempt += 1
            logpath = private_dir / (app + suffix + '-' + label + f'-attempt-{attempt}.log')
        with logpath.open('x') as log:
            result = subprocess.run([CLI, *args], cwd=BENCH, stdout=log, stderr=subprocess.STDOUT)
        print(app, label, 'exit', result.returncode, flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)

    if not marker.exists():
        if (BENCH / 'sites' / site).exists():
            raise SystemExit('Unmarked existing official site: inspect; never drop/force it.')
        run('new-site', ['new-site', site, '--db-name', 'ccm_upstream_' + app + suffix.replace('-', '_'),
            '--db-host', '127.0.0.1', '--db-port', '3307', '--db-socket', str(ROOT / 'mariadb.sock'),
            '--db-root-username', 'ccm_bootstrap', '--db-root-password', bootstrap['bootstrap_password'],
            '--admin-password', credentials['admin_password']])
        marker.write_text(json.dumps({'site': site, 'initial_state': 'new empty Frappe site',
            'allowed_apps': ['frappe'] + (['payments'] if payments else []) + (['erpnext'] if app == 'erpnext' else [])}))
    if app == 'erpnext':
        if payments:
            run('install-payments', ['--site', site, 'install-app', 'payments'])
        run('install', ['--site', site, 'install-app', 'erpnext'])
    # These site-local switches are the official Frappe CI test preparation.
    # Server Script remains disabled on Cencomun/baseline/recovery sites.
    for key, value in [('allow_tests', '1'), ('server_script_enabled', '1')]:
        run('config-' + key, ['--site', site, 'set-config', key, value, '--parse'])
    # Official command tests spawn new sites and read this value from conf.
    # Root login/password live only in the isolated Bench's private config.
    # Click positional values can start with '-'; keep secrets out of the
    # option parser without changing or regenerating existing credentials.
    run('config-admin', ['--site', site, 'set-config', '--', 'admin_password', credentials['admin_password']])
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
        if official_fx_fixtures:
            from capture_fx import capture
            capture(site, app + suffix + '-fx-before-bootstrap', load=True, direct_records=True)
        # Exactly the bootstrap module used by pinned ERPNext CI. Zero tests here
        # are fixture preparation only, never evidence of a passing suite.
        run('bootstrap', ['--site', site, 'run-tests', '--lightmode', '--module',
                          'erpnext.tests.bootstrap_test_data'])
    else:
        # Official hook before unit tests avoids the pinned runner's request=None
        # setup-wizard failure between categories. The hook still runs normally
        # inside the suite; nothing is skipped or monkeypatched.
        run('bootstrap', ['--site', site, 'execute', 'frappe.utils.install.before_tests'])
    # CLI -- execute starts a new process: no stale module map retained by
    # installation in memory. Do not globally flush shared Redis/other sites.
    run('module-map', ['--site', site, 'execute', 'frappe.setup_module_map'])
    from module_preflight import check
    check(site, app + suffix + '-module-preflight-preparation')
    print('Prepared official-only site:', site, flush=True)


def main(app, fresh=False, diagnostic=False, fixture_audit=False, official_fx_fixtures=False, fixture_order=False, final=False):
    with SuiteLock():
        if active_runners():
            raise RuntimeError('An official runner is active; do not change its sites or fixtures.')
        prepare(app, fresh, diagnostic, fixture_audit, official_fx_fixtures, fixture_order, final)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    parser.add_argument('--fresh', action='store_true', help='Use a separate new marked site; preserve the previous site intact.')
    parser.add_argument('--diagnostic', action='store_true', help='New official-only diagnostic site; preserve both previous sites.')
    parser.add_argument('--fixture-audit', action='store_true', help='Separate empty ERPNext site for preparation-order hypothesis.')
    parser.add_argument('--official-fx-fixtures', action='store_true', help='Load exact pinned Currency Exchange fixtures before native ERP bootstrap.')
    parser.add_argument('--fixture-order', action='store_true', help='New empty site for direct official FX records before any test module import.')
    parser.add_argument('--final', action='store_true', help='New official-only site for the authorized final full CI pass; preserve previous sites.')
    args = parser.parse_args()
    main(args.app, args.fresh, args.diagnostic, args.fixture_audit, args.official_fx_fixtures, args.fixture_order, args.final)
