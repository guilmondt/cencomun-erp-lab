"""Manage only this validation's loopback services and private runtime files."""

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
BENCH = ROOT / "bench"
STATE = ROOT / "processes.json"
LOGS = ROOT / "logs"


def specifications():
    return {
        "mariadb": [str(ROOT / "sysroot/usr/sbin/mariadbd"), f"--defaults-file={ROOT / 'mariadb.cnf'}"],
        "redis_cache": [str(ROOT / "sysroot/usr/bin/redis-server"), str(BENCH / "config/redis_cache.conf")],
        "redis_queue": [str(ROOT / "sysroot/usr/bin/redis-server"), str(BENCH / "config/redis_queue.conf")],
        "web": [str(BENCH / "env/bin/gunicorn"), "--bind", "127.0.0.1:8000", "--workers", "2",
                "--timeout", "120", "--chdir", str(BENCH / "sites"), "frappe.app:application"],
        "socketio": ["node", str(BENCH / "apps/frappe/socketio.js")],
        "worker": [str(ROOT / "bench-tools/bin/bench"), "worker", "--queue", "short,default,long"],
        "nginx": [str(ROOT / "sysroot/usr/sbin/nginx"), "-p", str(ROOT / "nginx") + "/",
                  "-c", str(ROOT / "nginx.conf"), "-g", "daemon off;"],
    }


def birth(pid):
    try:
        # The start tick identifies this PID even if the operating system reuses it.
        fields = Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except FileNotFoundError:
        return None


def start(names):
    LOGS.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    for name in names:
        previous = state.get(name)
        if previous and birth(previous["pid"]) == previous["birth"]:
            print(f"{name}: already running")
            continue
        if name == "socketio" and (ROOT / "socketio.sock").exists():
            if not (ROOT / "socketio.sock").is_socket():
                raise RuntimeError("Unexpected non-socket file at socketio.sock")
            (ROOT / "socketio.sock").unlink()
        with (LOGS / f"{name}.log").open("ab") as output:
            process = subprocess.Popen(specifications()[name], cwd=BENCH,
                                       stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        state[name] = {"pid": process.pid, "birth": birth(process.pid)}
        time.sleep(0.1)
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited; inspect private log {LOGS / (name + '.log')}")
        print(f"{name}: started")
    STATE.write_text(json.dumps(state, indent=2))


def stop(names):
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    for name in names:
        process = state.get(name)
        if not process:
            continue
        pid = process["pid"]
        if birth(pid) == process["birth"]:
            os.killpg(pid, signal.SIGTERM)
            for _ in range(100):
                if birth(pid) != process["birth"]:
                    break
                time.sleep(0.1)
            else:
                # Never hard-kill a database: an unexplained shutdown failure is a failed check.
                raise RuntimeError(f"{name}: did not stop cleanly in 10 seconds")
        state.pop(name, None)
        print(f"{name}: stopped")
    STATE.write_text(json.dumps(state, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("services", nargs="*", choices=list(specifications()))
    args = parser.parse_args()
    names = args.services or list(specifications())
    if args.action == "start":
        start(names)
    elif args.action == "stop":
        stop(list(reversed(names)))
    else:
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        for name in names:
            process = state.get(name)
            alive = bool(process and birth(process["pid"]) == process["birth"])
            print(f"{name}: {'running' if alive else 'stopped'}")
