"""Copy a pinned Bench for upstream tests that create sites/change global config.

No Git worktree or Cencomun checkout is created. Upstream dependencies are
local clones at exactly the pinned SHAs; DB/Redis stay on the fixed services.
"""

import json
import shutil
import subprocess
from pathlib import Path

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


def main():
    if MARKER.exists():
        copy_compiled_assets()
        print('Marked isolated Bench already exists:', TARGET)
        return
    if TARGET.exists():
        raise SystemExit('Unmarked official Bench exists; inspect, never overwrite.')
    (TARGET / 'apps').mkdir(parents=True)
    (TARGET / 'sites').mkdir()
    (TARGET / 'logs').mkdir()
    shutil.copytree(SOURCE / 'env', TARGET / 'env', symlinks=True)
    for app in ['frappe', 'erpnext']:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE / 'apps' / app, text=True).strip()
        subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(SOURCE / 'apps' / app),
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


if __name__ == '__main__':
    main()
