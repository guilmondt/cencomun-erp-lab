"""Derived bounded cause evidence; never rewrites a native attempt/result."""
import argparse
import collections
import hashlib
import json
import re
from decimal import Decimal
from run import OUT, PRIVATE, redact


def write(label, data):
    with (OUT / (label + '.json')).open('x') as stream:
        stream.write(redact(json.dumps(data, indent=2)) + '\n')
    print(label)


def read_events(base):
    path = PRIVATE / (base + '-observations.jsonl')
    return [json.loads(line) for line in path.read_text().splitlines()]


def revaluation():
    base = 'erpnext-test_exchange_rate_revaluation-selected-attempt-1'
    result = json.loads((OUT / (base + '.json')).read_text())
    events = read_events(base)
    before = next(e for e in events if e['kind'] == 'native_state' and e['stage'] == 'before_test')
    creation = next(e for e in events if e['kind'] == 'journal_state' and
                    e['stage'] == 'set_exchange_rate_call' and e['docstatus'] == 0)
    changed = next(e for e in events if e['kind'] == 'journal_state' and
                   e['stage'] == 'set_exchange_rate_return' and e['docstatus'] == 0)
    submit = next(e for e in events if e['kind'] == 'journal_state' and
                  e['stage'] == 'before_submit_call' and e['docstatus'] == 1)
    debit = sum(Decimal(str(row['debit'])) for row in submit['accounts'])
    credit = sum(Decimal(str(row['credit'])) for row in submit['accounts'])
    assert debit - credit == Decimal('100') == Decimal(str(submit['difference']))
    assert creation['accounts'][0]['exchange_rate'] == 0
    assert changed['accounts'][0]['exchange_rate'] == 1
    assert creation['total_debit'] == creation['total_credit'] == 8000
    assert result['actual_tests_run'] == 1 and result['counts']['ERROR'] == 1
    native_fx = [e for e in events if e['kind'] == 'fx_return' and e['from_currency'] == 'USD']
    assert all(e['result'] == 0 and e['entries'] == [] and e['filters'] for e in native_fx)
    journal_fx = [e for e in events if e['kind'] == 'journal_fx_return']
    assert journal_fx and all(e['result'] == 1 for e in journal_fx)
    errors = [e for e in events if e['kind'] == 'native_fx_error_log']
    assert all('Official offline reproduction' in e['terminal_exception'] for e in errors)
    data = {'native_result': base + '.json', 'native_case_status': 'ERROR',
            'classification': 'DEMONSTRATED_NATIVE_JOURNAL_FALLBACK_IMBALANCE_UNDER_OFFLINE',
            'preceding_modules_executed_in_this_process': [],
            'native_preparation_state': before,
            'journal_before_native_save_validation': creation,
            'journal_after_native_rate_resolution': changed,
            'journal_before_native_submit_validation': submit,
            'native_fx_returns_with_filters': native_fx, 'journal_fx_returns': journal_fx,
            'native_error_logs': errors,
            'arithmetic': {'debit': str(debit), 'credit': str(credit), 'difference': str(debit-credit),
                'increment': '100 USD in account currency * (native fallback 1 - initial 0) = 100 INR',
                'initial_balancing_loss_row_unchanged': '8000 INR debit'},
            'cause': 'Official test disables stale rates. Six 2016 records remain intact but no record satisfies posting-date window. Native provider request is rejected offline; Journal Entry resolver returns exchange_rate or 1, changing the USD debit row from 0 to 100 INR after the loss row was computed. Native submit correctly rejects 8100/8000.',
            'limit': 'No eligible native rate within the test date window with these exact fixtures and offline mode. Passing requires an out-of-scope fixture/date policy, upstream behavior/pin change or provider access. None was attempted; no preparation defect demonstrated.',
            'rates_fabricated': 0, 'assertions_or_validators_changed': False,
            'native_case_repeated_after_cause_demonstrated': False}
    write('erpnext-revaluation-cause', data)


def historical_http():
    initial = json.loads((OUT / 'frappe-final-failure-diagnostics.json').read_text())
    revised = json.loads((OUT / 'frappe-final-failure-diagnostics-v2.json').read_text())
    revised_by_id = {e['id']: e for e in revised['cases']}
    rows = []
    for case in initial['cases']:
        if case['classification'] != 'DEMONSTRATED_LOCAL_HTTP_REFUSAL_CAUSE_UNKNOWN':
            continue
        current = revised_by_id[case['id']]
        assert current['classification'] == 'DEMONSTRATED_NATIVE_HTTP_MOCK_REJECTION'
        assert current['evidence_flags']['responses_mock_refused']
        assert not current['evidence_flags']['loopback_connection_refused']
        rows.append({'id': case['id'], 'status': case['status'],
            'corrected_classification': current['classification'],
            'native_trace_frames': current['native_trace_frames'],
            'private_trace_block_sha256': current['private_trace_block_sha256']})
    assert len(rows) == 26
    write('frappe-historical-http-reclassification', {
        'native_execution': 'frappe-ci-attempt-1.json', 'native_result_unchanged': 'FAIL',
        'native_execution_repeated': False, 'original_diagnostic_preserved': True,
        'prior_classification_incorrect': True, 'claimed_TCP_refusals': 26,
        'demonstrated_OS_TCP_refusals_in_these_traces': 0,
        'demonstrated_responses_mock_rejections': 26, 'cases': rows,
        'additional_mock_rejections_previously_UNKNOWN': 2,
        'historical_server_lifetime_unknown': True,
        'limit': 'Old web log was empty and no PID/listener telemetry was captured. It cannot establish historical server lifetime. These 26 exceptions demonstrably arose before socket transport.'})


def sequence(base):
    result = json.loads((OUT / (base + '.json')).read_text())
    events = read_events(base)
    discovered = [e for e in events if e['kind'] == 'native_module_discovery']
    ids = {identifier for e in discovered for identifier in e['test_ids']}
    discovery_source = 'Observed native loader in this process'
    if not discovered:
        reference_path = OUT / (result['app'] + '-discovery-final.json')
        reference = json.loads(reference_path.read_text())
        ids = {identifier for category in reference['categories'] for identifier in category['test_ids']
               if identifier.rsplit('.', 2)[0] in result['sequence']}
        discovery_source = ('Retained pinned native full discovery filtered to the explicitly selected modules; '
                            'not a fresh discovery execution. This process loaded the observer before the discovery instrumentation was added.')
    observed = {e['test'] for e in events if e['kind'] == 'test_stopped'}
    # Native loader discovery is observed in order, without early imports.
    statuses = {e['id']: e['status'] for e in result['cases']}
    statuses.update({e['id']: e['status'] for e in result.get('failure_headers', [])})
    methods = [{'id': identifier, 'status': statuses.get(identifier, 'NO_RESULT')}
               for identifier in sorted(ids)]
    transport = [e for e in events if e['kind'] in ('http_attempt', 'http_exception', 'native_mock_dispatch', 'external_http_rejected', 'external_transport_rejected')]
    data = {'native_result': base + '.json', 'native_count': result['actual_tests_run'],
        'scope': 'Bounded modules only; never a complete suite result',
        'native_discovery': discovered, 'discovery_source': discovery_source,
        'reference_discovery_ids': len(ids),
        'stopped_distinct_ids': len(observed), 'cases_by_id': methods,
        'no_result_ids': sorted(ids-observed), 'class_fixture_events': [e for e in result.get('failure_headers', []) if e['id'].endswith(('setUpClass','tearDownClass'))],
        'counts_by_event': dict(collections.Counter(e['kind'] for e in events)),
        'transport_events': transport,
        'server_sites_observed': sorted({e['site'] for e in events if e['kind'] == 'native_http_served' and e.get('site')}),
        'automatic_restarts_during_test': 0,
        'counts_not_added_to_full_CI': True}
    destination = OUT / (base + '-coverage.json')
    if destination.exists():
        data['supersedes'] = destination.name
        data['diagnostic_revision'] = 2
        data['prior_coverage_had_no_discovery_and_could_not_establish_zero_missing'] = True
        write(base + '-coverage-v2', data)
    else:
        write(base + '-coverage', data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['revaluation', 'historical-http', 'sequence'])
    parser.add_argument('--base')
    args = parser.parse_args()
    {'revaluation': revaluation, 'historical-http': historical_http,
     'sequence': lambda: sequence(args.base)}[args.kind]()
