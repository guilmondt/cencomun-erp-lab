"""Record the official application's discovered tests, not executed tests."""

import argparse
import json
import os
from pathlib import Path

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
REPO = Path(__file__).resolve().parents[2]


def main(app):
    os.chdir(BENCH / 'sites')
    import frappe
    from frappe.testing import TestConfig, TestRunner, discover_all_tests
    from frappe.testing.environment import _initialize_test_environment

    site = 'ccm-upstream-' + app + '.test'
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
        out = REPO / 'reports/evidence/frappe-official'
        (out / (app + '-discovery.json')).write_text(json.dumps(data, indent=2) + '\n')
        print('Official discovery only:', app, data['discovered_test_count'], 'tests; zero executed.')
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    main(parser.parse_args().app)
