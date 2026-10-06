"""Compare original failures with NEW scoped runs without rewriting full FAIL."""
import json
import re
from pathlib import Path
from run import OUT, PRIVATE
from publish import native_result_file

latest = {}
for path in sorted(OUT.glob('*-attempt-*.json'), key=lambda p: p.name):
    if not native_result_file(path):
        continue
    data = json.loads(path.read_text())
    if not data.get('observe') or not (data.get('module') or data.get('sequence')):
        continue  # An old full PASS event is not a new reproduction of a failure.
    for case in data['cases']:
        current = latest.get(case['id'])
        if current is None or data['recorded_utc'] > current['recorded_utc']:
            latest[case['id']] = {'status': case['status'], 'evidence': path.name,
                'scope': data['scope'], 'recorded_utc': data['recorded_utc']}

original = json.loads((OUT / 'erpnext-ci-attempt-1.json').read_text())
zero_cases = [c for c in original['failure_headers'] if c['exception'].endswith('ZeroDivisionError')]
raw = re.sub(r'\x1b\[[0-9;]*m', '', (PRIVATE / 'erpnext-ci-attempt-1.log').read_text())
rows = []
for case in zero_cases:
    method = case['id'].rsplit('.', 1)[-1]
    match = re.search(r'ERROR\s+' + re.escape(method) + r'\s+\(' + re.escape(case['id']) + r'\)', raw)
    frames, numeric = [], {}
    if match:
        end = raw.find('=' * 30, match.end())
        block = raw[match.end():end if end >= 0 else len(raw)]
        frames = re.findall(r'^  File .+$', block, re.M)
        for key, value in re.findall(r'^\s*(source_exchange_rate|target_exchange_rate) = (-?\d+(?:\.\d+)?)\s*$', block, re.M):
            numeric[key] = float(value)
    rows.append({'id': case['id'], 'original_status': case['status'],
        'original_exception': case['exception'], 'original_trace_frames': frames,
        'original_whitelisted_numeric_locals': numeric,
        'original_reason_get_exchange_rate_returned_zero': 'Not captured per case; zero alone does not distinguish disabled settings/provider error.',
        'latest_scoped_result': latest.get(case['id'], {'status': 'NOT_REPRODUCED_CURRENT'})})
assert len(rows) == 14 and all(r['latest_scoped_result']['status'] == 'PASS' for r in rows)
(OUT / 'zero-division-case-tracking.json').write_text(json.dumps({
    'original_full_status': 'FAIL', 'full_rerun_performed': False, 'cases': rows,
    'note': 'All 14 named cases reexecuted PASS with corrected preparation; original complete FAIL retained.'}, indent=2) + '\n')

tracking = []
for app, name in [('frappe', 'frappe-full-attempt-4.json'), ('erpnext', 'erpnext-ci-attempt-1.json')]:
    data = json.loads((OUT / name).read_text())
    for case in data.get('failure_headers', data['cases']):
        if case['status'] in ('FAIL', 'ERROR'):
            tracking.append({'app': app, 'original_full_evidence': name, 'original_event': case['id'],
                'original_status': case['status'], 'latest_scoped_result': latest.get(case['id'],
                    {'status': 'NOT_REPRODUCED_CURRENT', 'cause': 'No new result; see existing diagnostics for demonstrated causes. Unresolved causes remain UNKNOWN, not inevitable blockers or PASS.'})})
(OUT / 'original-failure-followup.json').write_text(json.dumps({
    'original_full_statuses': {'frappe': 'FAIL', 'erpnext': 'FAIL'}, 'rows': tracking,
    'note': 'Only new observed scoped runs count as follow-up. Unmatched events have no new result.'}, indent=2) + '\n')
from collections import Counter
print('New scoped follow-up of original failure events:', dict(Counter(
    (r['app'] + ':' + r['latest_scoped_result']['status']) for r in tracking)))
