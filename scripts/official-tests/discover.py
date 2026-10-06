"""Record the official application's discovered tests, not executed tests."""

import argparse
import json
import os
from pathlib import Path
from run import SuiteLock, active_runners

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
REPO = Path(__file__).resolve().parents[2]


def discover(app, fresh=False, final=False):
    if fresh and final:
        raise ValueError('Choose one official site slot.')
    suffix = '-final' if final else ('-fresh' if fresh else '')
    output = REPO / 'reports/evidence/frappe-official' / (app + '-discovery' + ('-final' if final else '') + '.json')
    if final and output.exists():
        raise FileExistsError('Final discovery already recorded; preserve it.')
    os.chdir(BENCH / 'sites')
    import frappe
    from frappe.testing import TestConfig, TestRunner, discover_all_tests
    from frappe.testing.environment import _initialize_test_environment

    site = 'ccm-upstream-' + app + suffix + '.test'
    cfg = TestConfig()
    _initialize_test_environment(site, cfg)
    try:
        runner = TestRunner(cfg=cfg)
        discover_all_tests([app], runner)
        categories = [{'category': category, 'test_count': suite.countTestCases(),
                       'test_ids': [test.id() for test in runner._iterate_suite(suite)]}
                      for category, suite in runner.per_app_categories[app].items()]
        data = {'app': app, 'site': site, 'scope': 'official default all-category server discovery',
                'executed_by_this_command': 0,
                'discovered_test_count': sum(c['test_count'] for c in categories),
                'categories': categories}
        output.write_text(json.dumps(data, indent=2) + '\n')
        print('Official discovery only:', app, data['discovered_test_count'], 'tests; zero executed.')
    finally:
        frappe.db.rollback()
        frappe.destroy()


def main(app, fresh=False, final=False):
    with SuiteLock():
        if active_runners():
            raise RuntimeError('An official runner is active; defer fixture-aware discovery.')
        discover(app, fresh, final)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    main(args.app, args.fresh, args.final)
