"""Classify only the two final CI attempts using whitelisted evidence."""
import collections
import hashlib
import json
import re
from run import OUT, PRIVATE, redact


def classify(block, events):
    terminal = re.findall(r'^((?:\w+\.)*\w*(?:Error|Exception)(?::[^\n]*)?)$', block, re.M)
    terminal = terminal[-1] if terminal else ''
    if '[Errno 30]' in terminal and 'Read-only file system' in terminal and '/home/' in terminal:
        return 'DEMONSTRATED_READONLY_HOME', 'Native traceback contains Errno 30 and a HOME path; no HOME workaround authorized.'
    if 'Official offline reproduction' in terminal:
        return 'DEMONSTRATED_OFFLINE_TRANSPORT_REJECTION', 'Explicit offline rejection is the terminal exception; no provider response is inferred.'
    if 'Connection refused' in terminal and '127.0.0.1' in block:
        return 'DEMONSTRATED_LOCAL_HTTP_REFUSAL_CAUSE_UNKNOWN', 'Terminal connection refusal and loopback URL in the native trace are demonstrated; endpoint availability cause remains UNKNOWN, not an inevitable blocker.'
    return 'UNKNOWN', 'Failure reproduced in this full pass; available evidence does not establish its cause.'


def publish(path):
    result = json.loads(path.read_text())
    raw = re.sub(r'\x1b\[[0-9;]*m', '', (PRIVATE / (path.stem + '.log')).read_text())
    stream = PRIVATE / (path.stem + '-observations.jsonl')
    events = [json.loads(line) for line in stream.read_text().splitlines()] if stream.exists() else []
    rows = []
    for case in result.get('failure_headers', []):
        method = case['id'].rsplit('.', 1)[-1]
        matches = list(re.finditer(r'^\s*' + case['status'] + r'\s+' + re.escape(method) +
                                   r'\s+\(([^)]+)\)', raw, re.M))
        match = next((m for m in matches if case['id'] == m[1] or case['id'].rsplit('.', 1)[0] == m[1]), None)
        block = ''
        if match:
            separator = re.search(r'^={30,}\s*$', raw[match.end():], re.M)
            end = match.end() + separator.start() if separator else len(raw)
            block = raw[match.end():end]
        linked = [e for e in events if e.get('test') == case['id']]
        category, cause = classify(block, linked)
        rows.append({**case, 'classification': category, 'cause': cause,
                     'native_trace_frames': re.findall(r'^  File .+$', block, re.M),
                     'private_trace_block_sha256': hashlib.sha256(block.encode()).hexdigest() if block else None,
                     'evidence_flags': {'read_only_errno30': '[Errno 30]' in block and 'Read-only file system' in block,
                                        'loopback_connection_refused': 'Connection refused' in block and '127.0.0.1' in block,
                                        'external_rejection_events': sum(e['kind'] in ('external_http_rejected', 'external_transport_rejected') for e in linked),
                                        'native_fx_error_logs': sum(e['kind'] == 'native_fx_error_log' for e in linked),
                                        'http_domain_forbidden': any(e['kind'] == 'http_response' and e.get('domain_forbidden') for e in linked)}})
    data = {'app': result['app'], 'site': result['site'], 'native_result': path.name,
            'status': result['status'], 'actual_tests_run': result['actual_tests_run'],
            'native_summary_complete': result.get('native_summary_complete', False),
            'counter_not_inferred_from_events': True, 'cases': rows,
            'classification_counts': dict(collections.Counter(r['classification'] for r in rows)),
            'unknowns_not_pass_or_inevitable_blocks': True,
            'external_transport_rejections': dict(collections.Counter(e['kind'] for e in events if e['kind'] in ('external_http_rejected', 'external_transport_rejected'))),
            'no_final_summary': None if result.get('native_summary_complete') else {
                'exit_code': result['exit_code'], 'observed_events': len(result['cases']),
                'phase': 'Native command terminated without its final summary; inspect private trace before attributing bootstrap/import cause.',
                'native_trace_frames': re.findall(r'^  File .+$', raw, re.M)[-20:]}}
    destination = OUT / (result['app'] + '-final-failure-diagnostics.json')
    with destination.open('x') as output:
        output.write(redact(json.dumps(data, indent=2)) + '\n')
    print(json.dumps({k: data[k] for k in ('app', 'status', 'classification_counts', 'native_summary_complete')}))


if __name__ == '__main__':
    for app in ('frappe', 'erpnext'):
        paths = [p for p in OUT.glob(app + '-ci-attempt-*.json')
                 if json.loads(p.read_text()).get('site') == 'ccm-upstream-' + app + '-final.test']
        if len(paths) != 1:
            raise ValueError('Exactly one final full attempt per app is required.')
        publish(paths[0])
