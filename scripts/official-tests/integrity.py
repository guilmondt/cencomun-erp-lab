"""Hash original Cencomun runtime without publishing files or credentials."""
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from run import ROOT, OUT, PRIVATE, REPO


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def snapshot():
    bench = ROOT / 'bench'
    files = {}
    for label, folder in [('env', bench / 'env'),
                          *[('app-' + app, (bench / 'apps' / app).resolve())
                            for app in ('frappe', 'erpnext', 'cencomun_erp')]]:
        for path in folder.rglob('*'):
            relative = path.relative_to(folder)
            if '.git' in relative.parts or '__pycache__' in relative.parts:
                continue
            if path.is_file() and not path.is_symlink():
                files[label + '/' + str(relative)] = digest(path)
    for path in (bench / 'sites').glob('*/site_config.json'):
        files['sites/' + str(path.relative_to(bench / 'sites'))] = digest(path)
    for name in ('common_site_config.json', 'apps.txt', 'assets/assets.json', 'assets/assets-rtl.json'):
        files['sites/' + name] = digest(bench / 'sites' / name)
    for path in sorted((REPO / 'fixtures/ccm-core-v1').rglob('*')):
        if path.is_file():
            files[str(path.relative_to(REPO))] = digest(path)
    files['versions.lock'] = digest(REPO / 'versions.lock')
    sources = []
    for app in ('frappe', 'erpnext'):
        folder = bench / 'apps' / app
        sources.append({'app': app, 'sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=folder, text=True).strip(),
                        'changes': subprocess.check_output(['git', 'status', '--porcelain'], cwd=folder, text=True).splitlines()})
    return {'files': files, 'sources': sources,
            'manifest_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


def main(stage, label='final'):
    if not __import__('re').fullmatch(r'[a-z0-9-]+', label):
        raise ValueError('Safe evidence label required.')
    private = PRIVATE / ('cencomun-' + label + '-integrity-before.json')
    data = snapshot()
    output = OUT / ('cencomun-' + label + '-integrity-' + stage + '.json')
    if output.exists():
        raise FileExistsError('Preserve existing integrity evidence.')
    if stage == 'before':
        with private.open('x') as stream:
            json.dump(data, stream)
        private.chmod(0o600)
        changed = []
    else:
        before = json.loads(private.read_text())
        changed = [name for name in sorted(set(before['files']) | set(data['files']))
                   if before['files'].get(name) != data['files'].get(name)]
    public = {'stage': stage, 'scope': 'Original Bench env/apps/site configuration and shared oracle file integrity; not a regression or cloud restore',
              'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'files_hashed': len(data['files']), 'manifest_sha256': data['manifest_sha256'],
              'original_sources': data['sources'], 'changed_file_paths': changed,
              'runtime_unchanged': not changed if stage == 'after' else None,
              'exclusions': ['.git', '__pycache__', 'logs', 'mutable database data', 'symlink targets outside explicitly scanned app directories']}
    with output.open('x') as stream:
        stream.write(json.dumps(public, indent=2) + '\n')
    print(json.dumps(public))
    if changed:
        raise SystemExit('Original runtime changed: investigate and repeat Cencomun regression.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('stage', choices=['before', 'after'])
    parser.add_argument('--label', default='final')
    args = parser.parse_args()
    main(args.stage, args.label)
