"""Manage only the copied Bench's worker; queue names differ from Cencomun."""

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path('/workspace/.local/frappe-integral')
BENCH = ROOT / 'official-bench'
PRIVATE = ROOT / 'official-tests'
STATE = PRIVATE / 'worker.json'


def birth(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except FileNotFoundError:
        return None


def main(action):
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    alive = bool(state and birth(state['pid']) == state['birth'])
    if action == 'start':
        if alive:
            print('Official Bench worker already running')
            return
        with (PRIVATE / 'isolated-worker.log').open('ab') as log:
            process = subprocess.Popen([str(ROOT / 'bench-tools/bin/bench'), 'worker',
                                        '--queue', 'short,default,long'], cwd=BENCH,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        state = {'pid': process.pid, 'birth': birth(process.pid), 'bench': str(BENCH)}
        STATE.write_text(json.dumps(state))
        time.sleep(1)
        if process.poll() is not None:
            raise SystemExit('Official worker exited; inspect its private log.')
        print('Official Bench worker started')
    elif action == 'stop':
        if alive:
            os.killpg(state['pid'], signal.SIGTERM)
            for _ in range(50):
                if birth(state['pid']) != state['birth']:
                    break
                time.sleep(0.2)
            else:
                raise SystemExit('Official worker did not stop cleanly; do not hard-kill.')
        STATE.unlink(missing_ok=True)
        print('Official Bench worker stopped')
    else:
        print('Official Bench worker:', 'running' if alive else 'stopped')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    main(parser.parse_args().action)
