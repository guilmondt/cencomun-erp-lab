"""Capture whitelisted native FX state; optionally load exact official fixtures.

Never calls get_exchange_rate, requests or another provider. No rate/date edit.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo
from run import BENCH, OUT, PRIVATE, SuiteLock, active_runners, redact


def strip_variables(raw):
    """Error Log includes traceback locals. Keep only frame identities and type."""
    return {'frames': re.findall(r'^  File .+$', raw, re.M),
            'terminal_exception': redact(raw.splitlines()[-1] if raw else ''),
            'raw_sha256': hashlib.sha256(raw.encode()).hexdigest()}


def capture(site, label, load=False, historical=False, direct_records=False):
    path = OUT / (label + '.json')
    if path.exists():
        raise FileExistsError('Preserve existing evidence; select a new label before any fixture operation.')
    import frappe
    os.chdir(BENCH / 'sites')
    frappe.init(site=site); frappe.connect(); frappe.set_user('Administrator')
    fixture = BENCH / 'apps/erpnext/erpnext/setup/doctype/currency_exchange/test_records.json'
    records = json.loads(fixture.read_text())
    before = frappe.get_all('Currency Exchange', fields=['date', 'from_currency', 'to_currency', 'exchange_rate', 'for_buying', 'for_selling'])
    bom_count_before = frappe.db.count('BOM')
    if load:
        if direct_records:
            # Importing the fixture TEST module instantiates ERPNext's master
            # bootstrap too early. These exact JSON records have Currency-only
            # links, already installed by ERPNext; use the native Document API.
            for record in records:
                doc = frappe.get_doc(record)
                doc.insert()
            frappe.db.commit()
        else:
            from frappe.tests.utils import make_test_records, toggle_test_mode
            toggle_test_mode(True)
            make_test_records('Currency Exchange', commit=True)
    settings = frappe.get_doc('Currency Exchange Settings')
    accounts = frappe.get_doc('Accounts Settings')
    data = {'site': site, 'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'provider_requests_performed_by_capture': 0,
            'fixture_source': str(fixture.relative_to(BENCH)),
            'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
            'official_fixture_records': records, 'native_fixture_load_requested': load,
            'load_method': 'frappe.get_doc(record).insert()' if direct_records else 'native fixture generator',
            'bom_count_before_fx_load': bom_count_before, 'bom_count_after_fx_load': frappe.db.count('BOM'),
            'currency_records_before': before,
            'currency_records_after': frappe.get_all('Currency Exchange', fields=['date', 'from_currency', 'to_currency', 'exchange_rate', 'for_buying', 'for_selling']),
            'settings': {k: settings.get(k) for k in ('disabled', 'service_provider', 'api_endpoint', 'use_http')},
            'request_parameters': [{'key': r.key, 'value': '[REDACTED]' if any(k in r.key.lower() for k in ('key', 'token', 'secret', 'password')) else r.value} for r in settings.req_params],
            'result_keys': [r.key for r in settings.result_key],
            'accounts_settings': {k: accounts.get(k) for k in ('allow_stale', 'stale_days', 'allow_pegged_currencies_exchange_rates')},
            'site_time_zone': frappe.get_system_settings('time_zone')}
    if historical:
        base = 'erpnext-test_payment_request-attempt-1'
        previous = json.loads((OUT / (base + '.json')).read_text())
        end = datetime.datetime.fromisoformat(previous['recorded_utc'])
        start = end - datetime.timedelta(seconds=previous['elapsed_seconds'])
        zone = ZoneInfo(data['site_time_zone'])
        logs = frappe.get_all('Error Log', filters={'method': 'Unable to fetch exchange rate',
            'creation': ['between', [start.astimezone(zone).replace(tzinfo=None), end.astimezone(zone).replace(tzinfo=None)]]},
            fields=['name', 'creation', 'method', 'error'], order_by='creation asc')
        data['historical_attempt'] = base
        data['historical_interval_utc'] = [start.isoformat(), end.isoformat()]
        data['historical_error_logs'] = [{'name': r.name, 'creation_site_time': str(r.creation),
            'creation_utc': r.creation.replace(tzinfo=zone).astimezone(datetime.timezone.utc).isoformat(),
            'method': r.method, **strip_variables(r.error)} for r in logs]
        data['five_failed_cases'] = [{k: c[k] for k in ('id', 'exception', 'message')} for c in previous['cases'] if c['status'] == 'ERROR']
        data['correlation_limit'] = ('Historical Error Log has no test ID. Interval and JUnit second-resolution timestamps '
            'associate the module, not an unambiguous log per case. New observer records the current native test ID.')
    frappe.db.rollback(); frappe.destroy()
    with path.open('x') as stream:
        stream.write(redact(json.dumps(data, indent=2, default=str)) + '\n')
    print(json.dumps({'evidence': str(path), 'records': len(data['currency_records_after']),
                      'historical_error_logs': len(data.get('historical_error_logs', []))}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--load-official-fixtures', action='store_true')
    parser.add_argument('--historical', action='store_true')
    parser.add_argument('--native-documents', action='store_true', help='Avoid test-module/bootstrap import side effects when loading before master data.')
    args = parser.parse_args()
    from run import ALLOWED_SITES
    if args.site not in ALLOWED_SITES or not re.fullmatch(r'[a-z0-9-]+', args.label):
        raise ValueError('Only marked official sites and safe evidence names.')
    with SuiteLock():
        if active_runners():
            raise RuntimeError('Preserve the active runner; do not modify or inspect transaction fixtures.')
        capture(args.site, args.label, args.load_official_fixtures, args.historical, args.native_documents)
