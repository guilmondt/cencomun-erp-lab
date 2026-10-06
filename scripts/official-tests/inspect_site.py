"""Publish only fixture identity/isolation metadata through read-only Frappe APIs."""

import argparse
import hashlib
import json
import os
import subprocess
import datetime
from pathlib import Path

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
REPO = Path(__file__).resolve().parents[2]


def main(app, fresh=False, final=False):
    if fresh and final:
        raise ValueError('Choose one official site slot.')
    import frappe

    suffix = '-final' if final else ('-fresh' if fresh else '')
    site = 'ccm-upstream-' + app + suffix + '.test'
    os.chdir(BENCH / 'sites')
    frappe.init(site, sites_path=str(BENCH / 'sites'))
    frappe.connect()
    try:
        apps = frappe.get_installed_apps()
        creation = json.loads((ROOT / 'official-tests' / (app + suffix + '-isolated-created.json')).read_text())
        expected = creation['allowed_apps']
        assert apps == expected
        assert not frappe.db.exists('DocType', 'CCM Order')
        assert not frappe.conf.get('ccm_lab_enabled')
        data = {'site': site, 'bench': str(BENCH), 'installed_apps': apps,
                'inspected_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'scope': 'Read-only site isolation inspection; not a suite result',
                'cencomun_installed': False, 'lab_enabled': False,
                'test_permissions': {'allow_tests': frappe.conf.allow_tests,
                                     'server_script_enabled': frappe.conf.server_script_enabled},
                'creation': creation,
                'sources': []}
        for application in apps:
            directory = BENCH / 'apps' / application
            tag = subprocess.run(['git', 'describe', '--tags', '--exact-match'], cwd=directory, text=True, capture_output=True)
            data['sources'].append({'app': application,
                'sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=directory, text=True).strip(),
                'tag': tag.stdout.strip() if tag.returncode == 0 else None,
                'changes': subprocess.check_output(['git', 'status', '--porcelain'], cwd=directory, text=True).splitlines()})
        if app == 'erpnext':
            data['standard_buying'] = frappe.get_doc('Price List', 'Standard Buying').as_dict()
            data['standard_buying'] = {key: data['standard_buying'][key]
                                      for key in ['name', 'currency', 'buying', 'selling', 'enabled']}
            assert data['standard_buying']['currency'] == 'INR'
            assert not frappe.db.exists('Company', {'name': 'Cencomun LAB'})
            data['lab_products_present'] = bool(frappe.db.exists('Item', 'P001'))
            assert not data['lab_products_present']
            data['official_company_count'] = frappe.db.count('Company')
        data['status'] = 'PASS'
        out = REPO / 'reports/evidence/frappe-official'
        out.mkdir(parents=True, exist_ok=True)
        destination = out / (app + '-preparation' + (suffix or '-primary') + '.json')
        if final:
            attempt = 1
            while destination.exists():
                attempt += 1
                destination = out / (app + '-preparation-final-inspection-' + str(attempt) + '.json')
        with destination.open('x' if final else 'w') as stream:
            stream.write(json.dumps(data, indent=2, default=str) + '\n')
        (out / (app + '-preparation.json')).write_text(json.dumps(data, indent=2, default=str) + '\n')
        print('PASS official-only fixture isolation:', app)
    finally:
        frappe.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    main(args.app, args.fresh, args.final)
