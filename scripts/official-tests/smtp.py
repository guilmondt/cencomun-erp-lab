"""Manage pinned SMTP4dev 3.7.1 on loopback, without relay or outbound delivery."""

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path
from worker import birth

ROOT = Path('/workspace/.local/frappe-integral')
TOOLS = ROOT / 'official-tools'
PRIVATE = ROOT / 'official-tests'
STATE = PRIVATE / 'smtp.json'


def main(action):
    data = json.loads(STATE.read_text()) if STATE.exists() else {}
    alive = bool(data and birth(data['pid']) == data['birth'])
    if action == 'start':
        if alive:
            print('SMTP4dev already running')
            return
        env = {**os.environ, 'DOTNET_BUNDLE_EXTRACT_BASE_DIR': str(TOOLS / 'dotnet-cache')}
        args = [str(TOOLS / 'smtp4dev/Rnwood.Smtp4dev'),
                '--baseappdatapath=' + str(TOOLS / 'smtp-data'), '--urls=http://127.0.0.1:3000',
                '--smtpport=2525', '--imapport=0', '--allowremoteconnections-',
                '--relaysmtpserver=', '--relayautomaticallyemails=']
        with (PRIVATE / 'smtp4dev.log').open('ab') as log:
            process = subprocess.Popen(args, env=env, cwd=TOOLS / 'smtp4dev',
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        STATE.write_text(json.dumps({'pid': process.pid, 'birth': birth(process.pid)}))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(60):
            if process.poll() is not None:
                raise SystemExit('SMTP4dev exited; inspect its private log.')
            try:
                with opener.open('http://127.0.0.1:3000/api/Messages', timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise SystemExit('SMTP4dev readiness timeout.')
        print('SMTP4dev 3.7.1: HTTP3000 and SMTP2525 ready; loopback, relay disabled')
    elif action == 'stop':
        if alive:
            os.killpg(data['pid'], signal.SIGTERM)
            for _ in range(50):
                if birth(data['pid']) != data['birth']:
                    break
                time.sleep(0.2)
            else:
                raise SystemExit('SMTP4dev did not stop cleanly.')
        STATE.unlink(missing_ok=True)
        print('SMTP4dev stopped')
    else:
        print('SMTP4dev:', 'running' if alive else 'stopped')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    main(parser.parse_args().action)
