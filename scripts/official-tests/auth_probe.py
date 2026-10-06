"""Read-only credential/context probe; no login, tracker deletion or rehash."""
import argparse
import json
import os
import sys
from run import ALLOWED_SITES, BENCH, OUT, SuiteLock, active_runners
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent / 'observer'))
import auth_diagnostics


def main(site, label):
    if site not in ALLOWED_SITES or not label.replace('-', '').isalnum():
        raise ValueError('Explicit isolated site and safe unique label required.')
    with SuiteLock():
        if active_runners():
            raise RuntimeError('Runner active; preserve its state.')
        os.chdir(BENCH / 'sites')
        import frappe
        rows = []
        frappe.init(site); frappe.connect()
        try:
            auth_diagnostics.snapshot(frappe, lambda kind, **data: rows.append({'kind': kind, **data}), 'read_only_probe')
        finally:
            frappe.destroy()
        with (OUT / (label + '.json')).open('x') as stream:
            stream.write(json.dumps({'site': site, 'persistent_credentials_reset': False,
                                     'login_or_check_password_called': False, 'events': rows}, indent=2) + '\n')
        print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('site'); parser.add_argument('label')
    args = parser.parse_args(); main(args.site, args.label)
