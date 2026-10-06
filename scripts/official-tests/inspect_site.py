"""Publish only fixture identity/isolation metadata through read-only Frappe APIs."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
REPO = Path(__file__).resolve().parents[2]


def main(app):
    import frappe

    site = 'ccm-upstream-' + app + '.test'
    os.chdir(BENCH / 'sites')
    frappe.init(site, sites_path=str(BENCH / 'sites'))
    frappe.connect()
    try:
        apps = frappe.get_installed_apps()
        expected = ['frappe'] + (['erpnext'] if app == 'erpnext' else [])
        assert apps == expected
        assert not frappe.db.exists('DocType', 'CCM Order')
        assert not frappe.conf.get('ccm_lab_enabled')
        data = {'site': site, 'bench': str(BENCH), 'installed_apps': apps,
                'cencomun_installed': False, 'lab_enabled': False,
                'test_permissions': {'allow_tests': frappe.conf.allow_tests,
                                     'server_script_enabled': frappe.conf.server_script_enabled},
                'creation': json.loads((ROOT / 'official-tests' / (app + '-isolated-created.json')).read_text()),
                'sources': []}
        for application in apps:
            directory = BENCH / 'apps' / application
            data['sources'].append({'app': application,
                'sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=directory, text=True).strip(),
                'tag': subprocess.check_output(['git', 'describe', '--tags', '--exact-match'], cwd=directory, text=True).strip(),
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
        (out / (app + '-preparation.json')).write_text(json.dumps(data, indent=2, default=str) + '\n')
        print('PASS official-only fixture isolation:', app)
    finally:
        frappe.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    main(parser.parse_args().app)
