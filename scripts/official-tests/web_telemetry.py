"""Read-only ownership/listener telemetry. No requests, signals or restarts."""
import hashlib
import json
import time
from pathlib import Path


def process(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
        return {'pid': pid, 'state': fields[0], 'ppid': int(fields[1]), 'start_ticks': fields[19]}
    except OSError:
        return {'pid': pid, 'state': 'GONE', 'start_ticks': None}


def listeners(port):
    rows = []
    for name in ('tcp', 'tcp6'):
        for line in Path('/proc/net/' + name).read_text().splitlines()[1:]:
            parts = line.split()
            address, number = parts[1].rsplit(':', 1)
            if int(number, 16) == port and parts[3] == '0A':
                rows.append({'address_hex': address, 'port': port, 'inode': parts[9]})
    return rows


def sample(web, port, logpath, stage):
    states = [process(web.pid)]
    # The bench entry process may exec or spawn its serving process.
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            row = process(int(entry.name))
            if row.get('ppid') == web.pid:
                states.append(row)
    listening = listeners(port)
    inodes = {r['inode'] for r in listening}
    for state in states:
        owned = []
        try:
            for descriptor in Path(f"/proc/{state['pid']}/fd").iterdir():
                try:
                    target = descriptor.readlink().as_posix()
                    if target.startswith('socket:[') and target[8:-1] in inodes:
                        owned.append(target[8:-1])
                except OSError:
                    pass
            state['owned_listener_inodes'] = sorted(set(owned))
        except OSError:
            state['ownership_unreadable'] = True
    return {'epoch': time.time(), 'stage': stage, 'web_processes': states,
            'web_exit_code': web.poll(), 'listeners': listening,
            'web_log_bytes': logpath.stat().st_size,
            'web_log_mtime_epoch': logpath.stat().st_mtime}


def record(path, web, port, logpath, stage):
    data = sample(web, port, logpath, stage)
    with path.open('a') as stream:
        stream.write(json.dumps(data) + '\n')


def publish(path, logpath):
    raw = logpath.read_bytes()
    return {'samples': [json.loads(line) for line in path.read_text().splitlines()],
            'web_log_sha256': hashlib.sha256(raw).hexdigest(),
            'web_log_bytes': len(raw),
            'web_log_output_retained_privately': True,
            'automatic_restarts_during_test': 0}
