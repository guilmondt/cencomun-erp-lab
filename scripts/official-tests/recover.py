"""Record an interrupted attempt without re-running it or inventing results."""

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from run import BENCH, PRIVATE, OUT, SuiteLock, active_runners, parse_results, parse_parallel_results


def interrupted_record(app, base, private=PRIVATE, out=OUT, bench=BENCH):
    if (out / (base + '.json')).exists():
        raise RuntimeError('Result already exists; preserve it, do not overwrite.')
    log = private / (base + '.log')
    xml = private / (base + '.xml')
    statepath = private / (base + '-running.json')
    state = json.loads(statepath.read_text()) if statepath.exists() else {}
    ci = state.get('ci_parallel', '-ci-attempt-' in base)
    rawxml = xml.read_text() if xml.exists() else ''
    truncated = False
    if ci:
        partial = parse_parallel_results(log.read_text(), app)
    else:
        valid_documents = []
        for document in re.split(r'(?=<\?xml)', rawxml):
            if not document.strip():
                continue
            try:
                ET.fromstring(document)
                valid_documents.append(document)
            except ET.ParseError:
                truncated = True
        partial = parse_results(''.join(valid_documents), log.read_text())
    site = state.get('site', 'ccm-upstream-' + app + '.test')
    return {'scope': 'full official server application discovery', 'app': app,
            'site': site, 'bench': str(bench), 'module': state.get('module'),
            'category': state.get('category', 'all'), 'attempt': int(base.rsplit('-', 1)[1]),
            'ci_parallel': ci, 'truncated_xml_document_preserved': truncated,
            'status': 'BLOCKED', 'interrupted': True, 'evidence_valid': True,
            'reason': 'No active runner, no final result; interrupted attempt preserved without rerun.',
            'command': state.get('command', f'bench --site {site} run-tests --app {app} --junit-xml-output {xml}'),
            'exit_code': None, 'elapsed_seconds': None,
            'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'actual_tests_run': None, 'completed_native_category_counts': partial['runner_counts_by_category'],
            'discovered_categories': partial['discovered_categories'],
            'junit_records': partial['junit_records'], 'counts': partial['counts'], 'cases': partial['cases'],
            **({'failure_headers': partial['failure_headers'],
                'observed_result_events': partial['observed_result_events'],
                'native_summary_complete': partial['native_summary_complete']} if ci else {}),
            'uncompleted_test_outcomes': 'UNKNOWN, not PASS and not inferred from progress characters',
            'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
            'xml_sha256': hashlib.sha256(xml.read_bytes()).hexdigest() if xml.exists() else None}


def main(app, base):
    with SuiteLock():
        if active_runners():
            raise RuntimeError('Official runner is active; observe it, do not recover or duplicate it.')
        record = interrupted_record(app, base)
        record['upstream_sha'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                                       cwd=BENCH / 'apps' / app, text=True).strip()
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / (base + '.json')).open('x') as destination:
            destination.write(json.dumps(record, indent=2) + '\n')
        print('Preserved incomplete attempt:', base, 'BLOCKED; full test count UNKNOWN')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    parser.add_argument('attempt', help='Existing basename, e.g. erpnext-full-attempt-2')
    args = parser.parse_args()
    if not args.attempt.startswith(args.app + '-') or '/' in args.attempt:
        parser.error('Attempt must be an existing basename for the selected app.')
    main(args.app, args.attempt)
