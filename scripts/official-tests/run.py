"""Invoke the unmodified official runner and publish real JUnit test outcomes.

The official runner writes a complete XML document for each test category into
the same file. Parse each document independently, without inventing counts for
discovery/setup failures. Raw logs and XML remain private.
"""

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import time
import os
import signal
import fcntl
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
PRIVATE = ROOT / 'official-tests'
OUT = REPO / 'reports/evidence/frappe-official'
ALLOWED_SITES = ['ccm-upstream-frappe.test', 'ccm-upstream-erpnext.test',
                 'ccm-upstream-frappe-fresh.test', 'ccm-upstream-erpnext-fresh.test']


class SuiteLock:
    """Refuse another official suite while one owns this Bench's fixtures."""

    def __init__(self, private=PRIVATE):
        self.path = private / 'suite.lock'

    def __enter__(self):
        self.path.parent.mkdir(mode=0o700, exist_ok=True)
        self.file = self.path.open('a+')
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close()
            raise RuntimeError('An official suite is active; inspect it, do not duplicate it.')
        return self

    def __exit__(self, *args):
        self.file.close()


def active_runners(bench=BENCH):
    result = []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            command = (process / 'cmdline').read_bytes().split(b'\0')
            if not {b'run-tests', b'run-parallel-tests'}.intersection(command):
                continue
            cwd = Path(os.readlink(process / 'cwd')).resolve()
            if bench.resolve() not in [cwd, *cwd.parents]:
                continue
            if (process / 'stat').read_text().split(') ', 1)[1].split()[0] != 'Z':
                result.append(int(process.name))
        except (OSError, IndexError):
            continue
    return result


def reserve_attempt(label, private=PRIVATE, out=OUT):
    """Atomically reserve a filename even before a running job publishes JSON."""
    attempt = 1
    while True:
        base = f'{label}-attempt-{attempt}'
        if (out / (base + '.json')).exists() or (private / (base + '.log')).exists():
            attempt += 1
            continue
        try:
            with (private / (base + '.reserved')).open('x'):
                pass
            return attempt, base
        except FileExistsError:
            attempt += 1


def redact(text):
    values = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if any(k in key.lower() for k in ['password', 'api_key', 'api_secret', 'encryption_key']):
                    # Official CI's literal mail password "test" is public
                    # fixture data; replacing it would destroy words like
                    # testing throughout tracebacks. Real generated secrets
                    # in these private files are at least eight characters.
                    if isinstance(item, str) and len(item) >= 8:
                        values.append(item)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for path in [ROOT / 'secrets.json', ROOT / 'core-private.json',
                 *PRIVATE.glob('*private.json'), BENCH / 'sites/common_site_config.json',
                 *(BENCH / 'sites').glob('*/site_config.json'),
                 *(ROOT / 'bench/sites').glob('*/site_config.json')]:
        if path.exists():
            walk(json.loads(path.read_text()))
    for value in sorted(set(values), key=len, reverse=True):
        text = text.replace(value, '[REDACTED]')
    # Native command tests generate temporary credentials and may delete their
    # site configs before result publication. Redact command/config fields too.
    text = re.sub(r'(--(?:(?:admin|db-root|db)-)?password(?:\s+|=))(\S+)', r'\1[REDACTED]', text)
    text = re.sub(r'(["\'](?:password|db_password|root_password|admin_password|api_key|api_secret|encryption_key)["\']\s*:\s*["\'])([^"\']*)(["\'])',
                  r'\1[REDACTED]\3', text, flags=re.I)
    return text


def parse_results(xml, log):
    cases = []
    documents = []
    for document in re.split(r'(?=<\?xml)', xml):
        if not document.strip():
            continue
        root = ET.fromstring(document)
        documents.append({k: root.attrib.get(k) for k in ['tests', 'failures', 'errors', 'skipped', 'time']})
        for node in root.iter('testcase'):
            kind = next((k for k in ['error', 'failure', 'skipped'] if node.find(k) is not None), None)
            detail = node.find(kind) if kind else None
            cases.append({'id': node.attrib.get('classname', '') + '.' + node.attrib['name'],
                          'seconds': float(node.attrib.get('time', 0)),
                          'status': {'error': 'ERROR', 'failure': 'FAIL', 'skipped': 'SKIP'}.get(kind, 'PASS'),
                          **({'exception': detail.attrib.get('type', ''),
                              'message': redact(detail.attrib.get('message', '')),
                              'traceback': redact(detail.text or '')} if kind else {})})
    actual_runs = [int(n) for n in re.findall(r'Ran (\d+) tests? in [\d.]+s', log)]
    discovered = [{'tests': int(n), 'category': category, 'app': app}
                  for n, category, app in re.findall(r'Running (\d+) ([\w-]+) tests for (\w+)', log)]
    counts = {key: sum(case['status'] == key for case in cases) for key in ['PASS', 'FAIL', 'ERROR', 'SKIP']}
    return {'actual_tests_run': sum(actual_runs), 'runner_counts_by_category': actual_runs,
            'discovered_categories': discovered, 'junit_records': len(cases),
            'counts': counts, 'cases': cases, 'xml_documents': len(documents)}


def parse_parallel_results(log, app):
    """Read the official CI runner's own counter and verbose result events.

    It does not emit JUnit. Never infer its final count from dots or announced
    discovery. Keep raw tracebacks/locals private; publish method outcomes only.
    """
    clean = re.sub(r'\x1b\[[0-9;]*m', '', log)
    summary = re.findall(r'^Tests: (\d+), Failing: (\d+), Errors: (\d+)\s*$', clean, re.M)
    current = None
    cases = []
    for line in clean.splitlines():
        if re.fullmatch(re.escape(app) + r'\.[\w.]+', line.strip()):
            current = line.strip()
        match = re.match(r'^\s+([✔✖=])\s+(test\w+)\b', line)
        if current and match:
            cases.append({'id': current + '.' + match[2],
                          'status': {'✔': 'PASS', '✖': 'FAILED_EVENT', '=': 'SKIP'}[match[1]]})
    complete = bool(summary)
    final = tuple(map(int, summary[-1])) if complete else None
    failures = []
    for match in re.finditer(r'^\s*(ERROR|FAIL)\s+(test\w+|setUpClass|tearDownClass)\s+\((' +
                             re.escape(app) + r'\.[\w.]+)\)', clean, re.M):
        method, qualified = match[2], match[3]
        identifier = qualified if qualified.endswith('.' + method) else qualified + '.' + method
        block_end = clean.find('=' * 30, match.end())
        block = clean[match.end():block_end if block_end >= 0 else len(clean)]
        exception = re.findall(r'^((?:\w+\.)*\w*(?:Error|Exception))(?::|\s*$)', block, re.M)
        failures.append({'id': identifier, 'status': match[1],
                         'exception': exception[-1] if exception else 'UNKNOWN'})
    counts = {'PASS': sum(c['status'] == 'PASS' for c in cases),
              'SKIP': sum(c['status'] == 'SKIP' for c in cases),
              'FAIL': final[1] if final else None, 'ERROR': final[2] if final else None}
    return {'actual_tests_run': final[0] if final else None,
            'runner_counts_by_category': [], 'discovered_categories': [],
            'junit_records': 0, 'xml_documents': 0, 'cases': cases, 'counts': counts,
            'native_summary_complete': complete, 'observed_result_events': len(cases),
            'failure_headers': failures,
            'result_format': 'official CI verbose text; not JUnit',
            'count_note': 'Native Tests counter is authoritative; events may include subtests/fixtures. '
                          'FAILED_EVENT has no inferred FAIL/ERROR subtype. Missing final summary leaves count unknown.'}


def run_suite(app, module=None, category=None, port=None, site=None, ci_parallel=False):
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if ci_parallel and (module or category):
        raise ValueError('CI runner covers every module; do not combine selection flags.')
    label = app + ('-ci' if ci_parallel else ('-' + module.rsplit('.', 1)[-1] if module else '-full'))
    if category:
        label += '-' + category
    # Reserve against BOTH completed and still-running attempts. Exclusive file
    # creation prevents concurrent runs from truncating each other's evidence.
    attempt, base = reserve_attempt(label)
    logpath, xmlpath = PRIVATE / (base + '.log'), PRIVATE / (base + '.xml')
    site = site or ('ccm-upstream-' + app + '.test')
    if site not in ALLOWED_SITES:
        raise ValueError('Only marked upstream sites are accepted.')
    args = ['--site', site, 'run-tests', '--app', app, '--junit-xml-output', str(xmlpath)]
    if ci_parallel:
        args = ['--site', site, 'run-parallel-tests', '--app', app,
                '--total-builds', '1', '--build-number', '1']
        if app == 'erpnext':
            args.append('--lightmode')
    if module:
        args += ['--module', module]
    if category:
        args += ['--test-category', category]
    start = time.monotonic()
    print('Starting:', 'bench', *args, flush=True)
    port = port or (8002 if app == 'frappe' else 8005)
    statepath = PRIVATE / (base + '-running.json')
    state = {'app': app, 'site': site, 'bench': str(BENCH), 'module': module,
             'category': category or 'all', 'attempt': attempt, 'command': 'bench ' + ' '.join(args),
             'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'driver_pid': os.getpid(), 'port': port, 'ci_parallel': ci_parallel}
    statepath.write_text(json.dumps(state, indent=2) + '\n')
    statepath.chmod(0o600)
    webargs = [str(ROOT / 'bench-tools/bin/bench'), '--site', site, 'serve',
               '--port', str(port), '--noreload']
    # Official serve sets its site explicitly. CI mode disables the interactive
    # debugger; there is no application monkeypatch or modified validation.
    with (PRIVATE / (base + '-web.log')).open('x') as web_log:
        web = subprocess.Popen(webargs, cwd=BENCH, env={**os.environ, 'CI': 'Yes'},
                               stdout=web_log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(60):
                if web.poll() is not None:
                    raise RuntimeError('Official web process exited: inspect its private log.')
                try:
                    with opener.open(f'http://127.0.0.1:{port}/api/method/ping', timeout=1) as response:
                        assert json.load(response)['message'] == 'pong'
                    break
                except (OSError, ValueError):
                    time.sleep(0.5)
            else:
                raise RuntimeError('Official site HTTP readiness timeout.')
            with logpath.open('x') as log:
                runner = subprocess.Popen([str(ROOT / 'bench-tools/bin/bench'), *args],
                                          cwd=BENCH, env={**os.environ, 'CI': 'Yes'},
                                          stdout=log, stderr=subprocess.STDOUT)
                state['runner_pid'] = runner.pid
                statepath.write_text(json.dumps(state, indent=2) + '\n')
                result_code = runner.wait()
        finally:
            if web.poll() is None:
                os.killpg(web.pid, signal.SIGTERM)
                web.wait(timeout=20)
    rawlog = logpath.read_text()
    parsed = (parse_parallel_results(rawlog, app) if ci_parallel else
              parse_results(xmlpath.read_text() if xmlpath.exists() else '', rawlog))
    status = 'FAIL' if parsed['counts']['FAIL'] or parsed['counts']['ERROR'] else (
        'BLOCKED' if result_code or not parsed['actual_tests_run'] else 'PASS')
    record = {'scope': 'full official server application discovery' if not module else 'official module regression',
              'app': app, 'site': site, 'bench': str(BENCH), 'module': module, 'category': category or 'all', 'attempt': attempt, 'status': status,
              'ci_parallel': ci_parallel,
              'command': 'bench ' + ' '.join(args), 'web_command': ' '.join(webargs), 'exit_code': result_code,
              'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'elapsed_seconds': round(time.monotonic() - start, 3),
              'upstream_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BENCH / 'apps' / app, text=True).strip(),
              'log_sha256': hashlib.sha256(logpath.read_bytes()).hexdigest(),
              **parsed}
    if (result_code or not parsed['actual_tests_run']) and not ci_parallel:
        record['diagnostic_tail'] = redact('\n'.join(rawlog.splitlines()[-75:]))
    (OUT / (base + '.json')).write_text(json.dumps(record, indent=2) + '\n')
    statepath.unlink(missing_ok=True)
    print(json.dumps({k: record[k] for k in ['app', 'status', 'exit_code', 'actual_tests_run', 'junit_records', 'counts']}, indent=2), flush=True)
    return 0 if status == 'PASS' else 1


def main(*args, **kwargs):
    with SuiteLock():
        if active_runners():
            raise RuntimeError('Native official runner is still active; do not launch another suite.')
        return run_suite(*args, **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', choices=['frappe', 'erpnext'])
    parser.add_argument('--module')
    parser.add_argument('--category', choices=['unit', 'integration'])
    parser.add_argument('--port', type=int)
    parser.add_argument('--site', choices=ALLOWED_SITES)
    parser.add_argument('--ci-parallel', action='store_true',
                        help='Native official CI runner, one shard covering all modules; ERPNext uses its CI lightmode.')
    args = parser.parse_args()
    raise SystemExit(main(args.app, args.module, args.category, args.port, args.site, args.ci_parallel))
