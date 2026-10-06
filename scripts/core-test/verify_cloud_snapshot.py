"""Read-only snapshot verification, run BEFORE checkout/install/seed/migration.

Copy this verifier from the reviewed preparation commit into /tmp in a NEW
cloud task. Its source location does not determine the repository under test.
Running it on the preparation machine is only a local rehearsal.
"""

import argparse
import datetime
import hashlib
import json
import socket
import subprocess
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path

SAVED_HEAD = 'fcf690dbc58b2b2dcf8d045c49976e3613e804cf'
PINS_HASH = '6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816'
UPSTREAM = {'frappe': '97a5dd93ca5883bcc9c4ef9834120c5cba397b67',
            'erpnext': 'fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba'}
ROOT = Path('/workspace/.local/frappe-integral')


def verify(repo, expected_commit, task_reference):
    def git(*args, folder=repo):
        return subprocess.check_output(['git', *args], cwd=folder, text=True).strip()

    assert git('rev-parse', 'HEAD') == expected_commit, 'saved checkout HEAD mismatch'
    assert git('branch', '--show-current') == 'lab/frappe-baseline', 'wrong branch'
    assert not git('status', '--porcelain', '--untracked-files=all'), 'snapshot checkout is not clean'
    assert hashlib.sha256((repo / 'versions.lock').read_bytes()).hexdigest() == PINS_HASH, 'pins changed'
    for app, sha in UPSTREAM.items():
        folder = ROOT / 'bench/apps' / app
        assert git('rev-parse', 'HEAD', folder=folder) == sha, 'upstream SHA mismatch: ' + app
        assert not git('status', '--porcelain', '--untracked-files=all', folder=folder), 'upstream modified: ' + app
    fixture_folder = repo / 'fixtures/ccm-core-v1'
    manifest = json.loads((fixture_folder / 'manifest.json').read_text())
    for entry in manifest['files']:
        assert hashlib.sha256((fixture_folder / entry['path']).read_bytes()).hexdigest() == entry['sha256'], 'fixture hash mismatch'
    assert (ROOT / 'core-site-created').read_text().strip() == 'ccm-core.test', 'missing site marker'
    config = json.loads((ROOT / 'bench/sites/ccm-core.test/site_config.json').read_text())
    assert config['db_name'] == 'ccm_core_lab'
    assert config.get('ccm_lab_enabled') == 1 and config.get('ccm_measure_queries', 0) == 0
    private = json.loads((ROOT / 'core-private.json').read_text())
    reader = private['users']['reader']
    headers = {'Authorization': 'token ' + reader['api_key'] + ':' + reader['api_secret']}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(base, path, native=False, authenticate=True):
        request_headers = {**(headers if authenticate else {}), **({'Host': 'ccm-core.test'} if native else {})}
        request = urllib.request.Request(base + path, headers=request_headers)
        with opener.open(request, timeout=30) as response:
            assert response.status == 200
            return json.load(response)

    native_base = 'http://127.0.0.1:8000'
    assert get(native_base, '/api/method/frappe.auth.get_logged_user', True)['message'] == reader['email']
    mapping = json.loads((repo / 'reports/evidence/frappe-core/http-mapping.json').read_text())
    assert mapping['company_id'] == 'CCM-LAB-001'
    assert mapping['warehouse'] == 'WH-LAB-001-HTTP - CLAB'
    query = urllib.parse.urlencode({'company_id': mapping['company_id'], 'q': 'P001'})
    found = get('http://127.0.0.1:8090', '/products/search?' + query)['items']
    product = [item for item in found if item['id'] == 'P001']
    assert len(product) == 1 and Decimal(product[0]['price']) == Decimal('50.00')
    native = get(native_base, '/api/resource/Item/P001', True)['data']
    assert native['ccm_id'] == 'P001' and Decimal(str(native['cashea_price'])) == Decimal('50.00')
    query = urllib.parse.urlencode({'company_id': mapping['company_id'], 'warehouse': mapping['warehouse']})
    stock = get('http://127.0.0.1:8090', '/inventory/P001?' + query)
    query = urllib.parse.urlencode({'filters': json.dumps({'item_code': 'P001', 'warehouse': mapping['warehouse']}),
                                    'fields': json.dumps(['actual_qty'])})
    bins = get(native_base, '/api/resource/Bin?' + query, True)['data']
    assert len(bins) == 1 and Decimal(str(bins[0]['actual_qty'])) == Decimal(stock['on_hand']) == Decimal('5')
    # Baseline proxy and consumer are also queried, without creating any effects.
    assert get('http://127.0.0.1:8080', '/api/method/ping', authenticate=False)['message'] == 'pong'
    with socket.create_connection(('127.0.0.1', 8091), timeout=5):
        pass
    return {'status': 'PASS', 'verification_kind': 'read-only retained snapshot probe',
            'cloud_task_reference': task_reference, 'machine_hostname': socket.gethostname(),
            'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'observed_commit': expected_commit, 'branch': 'lab/frappe-baseline',
            'versions_lock_sha256': PINS_HASH, 'upstream': UPSTREAM,
            'site': 'ccm-core.test', 'company': mapping['company_id'], 'warehouse': mapping['warehouse'],
            'authenticated_actor': reader['email'], 'product': 'P001',
            'price_usd': '50.00', 'stock_adapter': '5', 'stock_native': '5',
            'lab_enabled': True, 'query_measurement': False,
            'baseline_ping': 'pong', 'consumer_port_reachable': True,
            'fixture_file_count': len(manifest['files']),
            'note': 'A PASS proves cloud restoration only when task identity confirms a genuinely NEW task. No data was installed, seeded, migrated or reset.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path('/workspace/cencomun-erp-lab'))
    parser.add_argument('--expected-commit', default=SAVED_HEAD)
    parser.add_argument('--task-reference', required=True, help='Actual new task URL/ID; use LOCAL-REHEARSAL for local execution.')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.repo, args.expected_commit, args.task_reference), indent=2))
    except Exception as error:
        # No traceback/config/header can leak credentials through a failed probe.
        print(json.dumps({'status': 'FAIL', 'error_type': type(error).__name__,
                          'step': str(error) if isinstance(error, AssertionError) else 'See the cloud verification diagnosis; inspect private logs without exposing credentials.'}))
        raise SystemExit(1) from None
