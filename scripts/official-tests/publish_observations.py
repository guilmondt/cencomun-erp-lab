"""Publish whitelisted evidence from private observer streams, never raw logs."""
import collections
import hashlib
import json
from run import PRIVATE, OUT, redact

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
               'external_transport_rejected', 'stock_entry_validation', 'bom_routing_state', 'observation_error')
    errors = {c['id'] for c in result.get('cases', []) if c['status'] == 'ERROR'}
    errors.update(c['id'] for c in result.get('failure_headers', []) if c['status'] == 'ERROR')
    evidence = {'native_result': resultpath.name, 'scope': result['scope'],
                'private_stream_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'counts_by_event': dict(collections.Counter(r['kind'] for r in events)),
                'provider_response_or_rate_fabricated': False,
                'fx_error_log_test_links': [{'test': e['test'], 'native_error_log': e['name']}
                    for e in events if e['kind'] == 'native_fx_error_log' and e['test'] in errors],
                'events': [e for e in events if e['kind'] in allowed]}
    with destination.open('x') as stream:
        stream.write(redact(json.dumps(evidence, indent=2)) + '\n')
    print(destination.name, 'event records', len(evidence['events']))
