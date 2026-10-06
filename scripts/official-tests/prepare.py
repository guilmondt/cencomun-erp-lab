"""Create an upstream-only test site; never reset or reuse an unmarked site."""

import argparse
import json
import subprocess
from pathlib import Path
from run import SuiteLock, active_runners

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
CLI = str(ROOT / 'bench-tools/bin/bench')


def retained_native_admin(common_config, fallback_private):
    """Pinned install_db prefers loaded conf over --admin-password.

    Reuse the existing common credential; never update a user/password or
    common config. This aligns preparation of NEW isolated sites with native CI.
    """
    common = json.loads(common_config.read_text()).get('admin_password')
    if common:
        return {'admin_password': common}
    return {'admin_password': json.loads(fallback_private.read_text())['admin_password']}


def prepare(app, fresh=False, diagnostic=False, fixture_audit=False, official_fx_fixtures=False, fixture_order=False, final=False, cause=False, cause_fixed=False, auth_clean=False, auth_sequence=False, residual=False):
    if sum((fresh, diagnostic, fixture_audit, fixture_order, final, cause, cause_fixed, auth_clean, auth_sequence, residual)) > 1:
        raise ValueError('Choose one isolated site slot.')
    if (fixture_audit or fixture_order or official_fx_fixtures) and app != 'erpnext':
        raise ValueError('Official FX fixtures apply only to ERPNext.')
    if cause_fixed and app != 'frappe':
        raise ValueError('Corrected mock guard reproduction is Frappe only.')
    if (auth_clean or auth_sequence or residual) and app != 'frappe':
        raise ValueError('Bounded auth sites are Frappe only.')
    suffix = '-auth-clean' if auth_clean else ('-auth-sequence' if auth_sequence else ('-cause-fixed' if cause_fixed else ('-cause' if cause else ('-final' if final else ('-fixture-order' if fixture_order else ('-fixture-audit' if fixture_audit else ('-diagnostic' if diagnostic else ('-fresh' if fresh else ''))))))))
    site = 'ccm-upstream-' + app + suffix + '.test'
    if residual:
        suffix = '-residual'
        site = 'ccm-upstream-frappe-residual.test'
    private_dir = ROOT / 'official-tests'
    private_dir.mkdir(mode=0o700, exist_ok=True)
    marker = private_dir / (app + suffix + '-isolated-created.json')
    private = private_dir / (app + suffix + '-private.json')
    if (auth_clean or auth_sequence or residual) and (marker.exists() or (BENCH / 'sites' / site).exists()):
        raise RuntimeError('Preserve existing auth diagnostic site; do not rewrite its config/credentials. Use read-only probe or runner.')
    if not private.exists():
        # Reuse the already retained credential for NEW sites; never reset an
        # existing site/user or regenerate a persistent credential to pass tests.
        credentials = retained_native_admin(BENCH / 'sites/common_site_config.json',
                                            private_dir / 'frappe-cause-fixed-private.json')
        private.write_text(json.dumps(credentials))
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


def main(app, fresh=False, diagnostic=False, fixture_audit=False, official_fx_fixtures=False, fixture_order=False, final=False, cause=False, cause_fixed=False, auth_clean=False, auth_sequence=False, residual=False):
    with SuiteLock():
        if active_runners():
            raise RuntimeError('An official runner is active; do not change its sites or fixtures.')
        prepare(app, fresh, diagnostic, fixture_audit, official_fx_fixtures, fixture_order, final, cause, cause_fixed, auth_clean, auth_sequence, residual)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    parser.add_argument('--fresh', action='store_true', help='Use a separate new marked site; preserve the previous site intact.')
    parser.add_argument('--diagnostic', action='store_true', help='New official-only diagnostic site; preserve both previous sites.')
    parser.add_argument('--fixture-audit', action='store_true', help='Separate empty ERPNext site for preparation-order hypothesis.')
    parser.add_argument('--official-fx-fixtures', action='store_true', help='Load exact pinned Currency Exchange fixtures before native ERP bootstrap.')
    parser.add_argument('--fixture-order', action='store_true', help='New empty site for direct official FX records before any test module import.')
    parser.add_argument('--final', action='store_true', help='New official-only site for the authorized final full CI pass; preserve previous sites.')
    parser.add_argument('--cause', action='store_true', help='New official-only site for bounded cause diagnostics; preserve all previous sites.')
    parser.add_argument('--cause-fixed', action='store_true', help='New Frappe site after proven offline/native-mock correction; preserve failed site.')
    parser.add_argument('--auth-clean', action='store_true', help='New native-CI Frappe site for clean representative auth/context cases; retained credential reused.')
    parser.add_argument('--auth-sequence', action='store_true', help='Separate new native-CI Frappe site for preceding-module hypotheses; retained credential reused.')
    parser.add_argument('--residual', action='store_true', help='New native-CI Frappe site for the authorized residual IDs; preserve all prior sites and credentials.')
    args = parser.parse_args()
    main(args.app, args.fresh, args.diagnostic, args.fixture_audit, args.official_fx_fixtures, args.fixture_order, args.final, args.cause, args.cause_fixed, args.auth_clean, args.auth_sequence, args.residual)
