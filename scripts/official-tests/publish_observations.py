"""Publish whitelisted evidence from private observer streams, never raw logs."""
import collections
import hashlib
import json
from run import PRIVATE, OUT, redact


def selected_events(events, result):
    if not (result.get('ci_parallel') and result.get('site', '').endswith('-final.test')):
        return events
    failed = {c['id'] for c in result.get('cases', []) if c['status'] in ('ERROR', 'FAIL', 'FAILED_EVENT')}
    failed.update(c['id'] for c in result.get('failure_headers', []))
    boundaries = {}
    for index, event in enumerate(events):
        if event['kind'] == 'native_state' and event.get('test'):
            module = event['test'].rsplit('.', 2)[0]
            key = (module, event['stage'])
            if key not in boundaries:
                boundaries[key] = [index, index]
            else:
                boundaries[key][1] = index
    keep = {i for indexes in boundaries.values() for i in indexes}
    return [event for index, event in enumerate(events)
            if event['kind'] != 'native_state' or index in keep or event.get('test') in failed]


def main():
    for path in sorted(PRIVATE.glob('*-observations.jsonl')):
        base = path.name.removesuffix('-observations.jsonl')
        resultpath = OUT / (base + '.json')
        if not resultpath.exists():
            continue  # Never publish a running/incomplete stream as complete.
        result = json.loads(resultpath.read_text())
        destination = OUT / (base + '-observations.json')
        if destination.exists():
            assert json.loads(destination.read_text())['private_stream_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
            continue
        events = [json.loads(line) for line in path.read_text().splitlines()]
        # These fields are emitted by the observer's whitelist. No headers,
        # cookies, response bodies, URLs with query tokens or traceback locals.
        allowed = ('observer_started', 'module_map_return', 'native_state', 'fx_return',
                   'native_fx_error_log', 'http_response', 'external_http_rejected',
                   'external_transport_rejected', 'stock_entry_validation', 'bom_routing_state', 'observation_error',
                   'journal_state', 'journal_fx_return', 'http_attempt', 'http_exception',
                   'native_get_url', 'native_http_served', 'native_mock_transition', 'native_mock_dispatch',
                   'native_module_discovery', 'auth_state', 'request_context_transition',
                   'auth_config_loaded', 'auth_class_import', 'native_auth_operation',
                   'native_http_exception', 'native_todo_workflow_call', 'native_cache_html',
                   'auth_http_response', 'native_password_write_call', 'native_auth_tracker',
                   'native_oauth_assertion_state', 'native_http_reply',
                   'residual_native_exception', 'residual_email_state')
        errors = {c['id'] for c in result.get('cases', []) if c['status'] == 'ERROR'}
        errors.update(c['id'] for c in result.get('failure_headers', []) if c['status'] == 'ERROR')
        evidence = {'native_result': resultpath.name, 'scope': result['scope'],
                    'private_stream_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'counts_by_event': dict(collections.Counter(r['kind'] for r in events)),
                    'provider_response_or_rate_fabricated': False,
                    'fx_error_log_test_links': [{'test': e['test'], 'native_error_log': e['name']}
                        for e in events if e['kind'] == 'native_fx_error_log' and e['test'] in errors],
                    'selection': 'Full CI: module boundary native states, all failed-case states and all other allowed events; full stream private and hashed' if result.get('ci_parallel') and result.get('site', '').endswith('-final.test') else 'All allowed events',
                    'events': [e for e in selected_events(events, result) if e['kind'] in allowed]}
        with destination.open('x') as stream:
            stream.write(redact(json.dumps(evidence, indent=2)) + '\n')
        print(destination.name, 'event records', len(evidence['events']))


if __name__ == '__main__':
    main()
