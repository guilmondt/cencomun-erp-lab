"""Download/check/extract exact official CI test infrastructure without root."""

import hashlib
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path('/workspace/.local/frappe-integral')
TOOLS = ROOT / 'official-tools'


def main():
    lock = json.loads((REPO / 'labs/frappe/integral/official-system.lock.json').read_text())
    downloads = TOOLS / 'downloads'
    downloads.mkdir(parents=True, exist_ok=True)
    for artifact in lock['artifacts']:
        source = downloads / artifact['file']
        if not source.exists():
            with urllib.request.urlopen(artifact['url'], timeout=60) as response:
                source.write_bytes(response.read())
        assert hashlib.sha256(source.read_bytes()).hexdigest() == artifact['sha256'], 'Artifact checksum mismatch: ' + artifact['name']
        target = TOOLS / artifact['target']
        target.mkdir(exist_ok=True)
        if artifact['format'] == 'deb':
            subprocess.run(['dpkg-deb', '--extract', str(source), str(target)], check=True)
        else:
            with zipfile.ZipFile(source) as archive:
                for name in archive.namelist():
                    assert not name.startswith('/') and '..' not in Path(name).parts
                archive.extractall(target)
    smtp = TOOLS / 'smtp4dev/Rnwood.Smtp4dev'
    smtp.chmod(0o700)
    (TOOLS / 'bin').mkdir(exist_ok=True)
    wrapper = TOOLS / 'bin/wkhtmltopdf'
    wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'
        'export LD_LIBRARY_PATH=/workspace/.local/frappe-integral/official-tools/wkhtmltox/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n'
        'exec /workspace/.local/frappe-integral/official-tools/wkhtmltox/usr/local/bin/wkhtmltopdf "$@"\n')
    wrapper.chmod(0o700)
    subprocess.run([str(wrapper), '--version'], check=True)
    print('Verified/extracted exact test-only infrastructure:', [a['name'] for a in lock['artifacts']])


if __name__ == '__main__':
    main()
