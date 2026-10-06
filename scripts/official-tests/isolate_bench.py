"""Copy a pinned Bench for upstream tests that create sites/change global config.

No Git worktree or Cencomun checkout is created. Upstream dependencies are
local clones at exactly the pinned SHAs; DB/Redis stay on the fixed services.
"""

import json
import shutil
import subprocess
import argparse
import datetime
from pathlib import Path
from run import SuiteLock, active_runners
from worker import STATE, birth

ROOT = Path('/workspace/.local/frappe-integral')
SOURCE = ROOT / 'bench'
TARGET = ROOT / 'official-bench'
MARKER = ROOT / 'official-tests/isolated-bench.json'


def copy_compiled_assets(source=SOURCE, target=TARGET):
    """Git clones omit ignored build outputs needed by official PDF tests."""
    for app in ['frappe', 'erpnext']:
        compiled = source / 'apps' / app / app / 'public/dist'
        if not compiled.is_dir():
            raise RuntimeError('Missing pinned compiled assets: ' + app)
        shutil.copytree(compiled, target / 'apps' / app / app / 'public/dist',
                        dirs_exist_ok=True)
    for name in ['assets.json', 'assets-rtl.json']:
        shutil.copy2(source / 'sites/assets' / name, target / 'sites/assets' / name)


def clone_pinned_apps():
    (TARGET / 'apps').mkdir(parents=True)
    sources = {app: SOURCE / 'apps' / app for app in ['frappe', 'erpnext']}
    payments = ROOT / 'official-tests/payments-prepared.json'
    if payments.exists():
        sources['payments'] = Path(json.loads(payments.read_text())['source'])
    for app, source in sources.items():
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        if app == 'payments' and sha != json.loads(payments.read_text())['sha']:
            raise RuntimeError('Payments fixture SHA changed; preserve and inspect it.')
        subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(source),
                        str(TARGET / 'apps' / app)], check=True, capture_output=True)
        subprocess.run(['git', 'checkout', '--detach', sha], cwd=TARGET / 'apps' / app,
                       check=True, capture_output=True)
        # Local dependency links are runtime files, not upstream source edits.
        with (TARGET / 'apps' / app / '.git/info/exclude').open('a') as exclude:
            exclude.write('\n/node_modules\n')
        node_modules = SOURCE / 'apps' / app / 'node_modules'
        if node_modules.exists():
            (TARGET / 'apps' / app / 'node_modules').symlink_to(node_modules)
        package = TARGET / 'env/lib/python3.14/site-packages' / (app + '.pth')
        package.write_text(str(TARGET / 'apps' / app) + '\n')


def archive_test_sources(apps, destination):
    if destination.exists():
        raise RuntimeError('Source archive exists; never overwrite it.')
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    apps.rename(destination)


def prepare(refresh=False):
    if MARKER.exists():
        if refresh:
            state = json.loads(STATE.read_text()) if STATE.exists() else {}
            if state and birth(state['pid']) == state['birth']:
                raise RuntimeError('Stop the official worker before refreshing its imported test sources.')
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            archived = MARKER.parent / 'source-history' / stamp / 'apps'
            archive_test_sources(TARGET / 'apps', archived)
            clone_pinned_apps()
            print('Preserved generated test sources:', archived)
        copy_compiled_assets()
        print('Marked isolated Bench already exists:', TARGET)
        return
    if refresh:
        raise RuntimeError('Cannot refresh an unmarked official Bench.')
    if TARGET.exists():
        raise SystemExit('Unmarked official Bench exists; inspect, never overwrite.')
    (TARGET / 'sites').mkdir(parents=True)
    (TARGET / 'logs').mkdir()
    shutil.copytree(SOURCE / 'env', TARGET / 'env', symlinks=True)
    clone_pinned_apps()
    # Cencomun is deliberately absent from this copied Python environment.
    (TARGET / 'env/lib/python3.14/site-packages/cencomun_erp.pth').unlink(missing_ok=True)
    shutil.copytree(SOURCE / 'config', TARGET / 'config')
    shutil.copytree(SOURCE / 'sites/assets', TARGET / 'sites/assets', symlinks=True)
    for app in ['frappe', 'erpnext']:
        asset_link = TARGET / 'sites/assets' / app
        if asset_link.is_symlink():
            asset_link.unlink()
            asset_link.symlink_to(TARGET / 'apps' / app / app / 'public')
    copy_compiled_assets()
    (TARGET / 'sites/apps.txt').write_text('frappe\nerpnext\n')
    config = json.loads((SOURCE / 'sites/common_site_config.json').read_text())
    bootstrap = json.loads((ROOT / 'secrets.json').read_text())
    config.update({'db_host': '127.0.0.1', 'db_port': 3307, 'db_socket': str(ROOT / 'mariadb.sock'),
                   'root_login': 'ccm_bootstrap', 'root_password': bootstrap['bootstrap_password']})
    (TARGET / 'sites/common_site_config.json').write_text(json.dumps(config, indent=2))
    (TARGET / 'sites/common_site_config.json').chmod(0o600)
    (TARGET / 'Procfile').write_text('web: bench serve --port 8002\n')
    MARKER.write_text(json.dumps({'bench': str(TARGET), 'source': str(SOURCE),
                                 'apps': ['frappe', 'erpnext'], 'pins_changed': False}, indent=2))
    print('Created isolated pinned Bench:', TARGET)


def main(refresh=False):
    with SuiteLock():
        if active_runners():
            raise RuntimeError('An official runner is active; do not modify its copied Bench.')
        prepare(refresh)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-test-sources', action='store_true',
                        help='Preserve generated files and recreate only copied apps at the same SHAs; no site reset.')
    main(parser.parse_args().refresh_test_sources)
