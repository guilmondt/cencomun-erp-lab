"""Verify native module maps against installed apps; repair only stale site cache."""
import json
import os
from pathlib import Path
from run import BENCH, OUT, PRIVATE, ALLOWED_SITES, SuiteLock, active_runners


def expected_map(apps, modules):
    return {module.strip().lower().replace(' ', '_').replace('-', '_'): app for app in apps for module in modules[app]}


def check(site, label):
    destination = OUT / (label + '.json')
    if destination.exists():
        raise FileExistsError('Preserve existing module evidence before any cache operation.')
    import frappe
    from frappe.modules.utils import get_module_app
    os.chdir(BENCH / 'sites')
    frappe.init(site); frappe.connect(); frappe.set_user('Administrator')
    apps = frappe.get_installed_apps()
    import importlib
    origins = {app: str(Path(importlib.import_module(app).__file__).resolve()) for app in apps}
    for app, origin in origins.items():
        assert Path(origin).is_relative_to(BENCH / 'apps' / app), 'Helper shadows official app: ' + app
    modules = {app: frappe.get_module_list(app) for app in apps}
    assert all(modules.values()), 'Installed official app with empty module list; preserve and diagnose.'
    expected = expected_map(apps, modules)
    before = dict(frappe.local.module_app)
    mismatch = {m: {'expected': a, 'observed': before.get(m)} for m, a in expected.items() if before.get(m) != a}
    if mismatch:
        # The key is db_name|app_modules, not shared. No clear-all/Redis flush.
        frappe.cache.delete_value('app_modules')
        frappe.setup_module_map()
    after = {m: get_module_app(m) for m in expected}
    assert after == expected, 'Native resolver still inconsistent; preserve the failure.'
    data = {'site': site, 'installed_apps': apps, 'import_origins': origins,
            'apps_txt': (BENCH / 'sites/apps.txt').read_text().splitlines(),
            'modules_txt': modules, 'before': before, 'expected': expected, 'after': after,
            'mismatch': mismatch, 'repair_applied': bool(mismatch),
            'repair_scope': 'native db_name|app_modules only; no shared cache, permission or source change',
            'native_resolver_verified': True}
    frappe.db.rollback(); frappe.destroy()
    with destination.open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')
    print('Native module preflight:', site, 'PASS', 'repair:', bool(mismatch))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--site', choices=ALLOWED_SITES, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    import re
    if not re.fullmatch('[a-z0-9-]+', args.label):
        raise ValueError('Safe evidence basename required')
    with SuiteLock():
        if active_runners():
            raise RuntimeError('Do not change state while a native runner is active')
        check(args.site, args.label)
