"""Reproduce the old helper namespace collision without a site/DB/cache/network."""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from run import BENCH, PRIVATE, REPO, OUT

original = subprocess.check_output(['git', 'show',
    '8158b6803e4951a3fe66372578667f6cd8cab5a5:scripts/official-tests/payments.py'], cwd=REPO)
program = """
import sys,json
sys.path[:0] = sys.argv[1:]
import frappe,payments
print(json.dumps({'package': payments.__package__, 'origin': payments.__file__,
                  'native_modules': frappe.get_module_list('payments')}))
"""
with tempfile.TemporaryDirectory(dir=PRIVATE) as folder:
    file = Path(folder) / 'payments.py'; file.write_bytes(original)
    shadowed = json.loads(subprocess.check_output([str(BENCH / 'env/bin/python'), '-c', program,
        folder, str(REPO / 'scripts/official-tests')], text=True))
    actual = json.loads(subprocess.check_output([str(BENCH / 'env/bin/python'), '-c', program,
        str(REPO / 'scripts/official-tests')], text=True))
assert shadowed['native_modules'] == [] and not shadowed['package']
assert actual['native_modules'] == ['Payments', 'Payment Gateways'] and actual['package'] == 'payments'
shadowed['origin'] = 'retained copy of 8158:scripts/official-tests/payments.py'
data = {'source_commit': '8158b6803e4951a3fe66372578667f6cd8cab5a5',
        'old_helper_sha256': hashlib.sha256(original).hexdigest(),
        'before_rename': shadowed, 'after_rename': actual,
        'site_initialized': False, 'database_or_cache_touched': False, 'provider_requests': 0,
        'conclusion': 'Helper file shadows package and yields empty native module list; rename removes collision.'}
destination = OUT / 'payments-shadow-proof.json'
with destination.open('x') as stream:
    stream.write(json.dumps(data, indent=2) + '\n')
print('Payments helper collision reproduced without site/DB/cache: confirmed')
