"""Inventory results/absences from one new full CI attempt, never old PASS."""
import argparse
import collections
import json
from run import OUT


def publish(app):
    paths = [p for p in OUT.glob(app + '-ci-attempt-*.json')
             if json.loads(p.read_text()).get('site') == 'ccm-upstream-' + app + '-final.test']
    if len(paths) != 1:
        raise ValueError('Exactly one completed final attempt is required.')
    result = json.loads(paths[0].read_text())
    discovery_path = OUT / (app + '-discovery-final.json')
    discovery = json.loads(discovery_path.read_text())
    discovered = {identifier for c in discovery['categories'] for identifier in c['test_ids']}
    by_id = collections.defaultdict(list)
    for event in result['cases']:
        by_id[event['id']].append(event['status'])
    headers = collections.defaultdict(list)
    for failure in result.get('failure_headers', []):
        headers[failure['id']].append(failure)
    rows = []
    for identifier in sorted(discovered | set(by_id) | set(headers)):
        statuses = set(by_id[identifier])
        statuses.update(h['status'] for h in headers[identifier])
        if not statuses:
            status = 'NO_RESULT'
        elif 'ERROR' in statuses:
            status = 'ERROR'
        elif 'FAIL' in statuses:
            status = 'FAIL'
        elif 'FAILED_EVENT' in statuses:
            status = 'FAILED_EVENT'
        elif len(statuses) == 1:
            status = next(iter(statuses))
        else:
            status = 'MIXED_EVENTS'
        rows.append({'id': identifier, 'in_discovery_manifest': identifier in discovered,
                     'native_verbose_events': by_id[identifier], 'native_failure_headers': headers[identifier],
                     'status': status})
    no_result = [r['id'] for r in rows if r['status'] == 'NO_RESULT']
    data = {'app': app, 'site': result['site'], 'native_attempt': paths[0].name,
            'discovery_manifest': discovery_path.name,
            'discovered_test_count': discovery['discovered_test_count'],
            'distinct_discovered_ids': len(discovered),
            'actual_tests_run': result['actual_tests_run'],
            'native_summary_complete': result.get('native_summary_complete', False),
            'native_counts': result['counts'], 'observed_result_events': len(result['cases']),
            'distinct_id_status_counts': dict(collections.Counter(r['status'] for r in rows)),
            'discovered_ids_without_result': no_result, 'cases': rows,
            'notes': ['Only this final full attempt supplies results; no modular/previous PASS is joined.',
                      'Distinct IDs, fixture/subtest events and discovery are not the native executed-test counter.',
                      'NO_RESULT records missing evidence, never PASS; no execution count is inferred.',
                      'Native CI uses its own discovery rules, including the built-in test_runner.py exclusion; no added case filter.',
                      'Native verbose output does not include skip reasons; reasons are not invented.']}
    destination = OUT / (app + '-final-case-inventory.json')
    with destination.open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')
    print({k: data[k] for k in ('app', 'actual_tests_run', 'distinct_id_status_counts')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('app', choices=['frappe', 'erpnext'])
    publish(parser.parse_args().app)
