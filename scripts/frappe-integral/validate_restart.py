"""Prove a complete graceful stop/restart and repeat the real-site checks."""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path("/workspace/.local/frappe-integral")
SCRIPTS = Path(__file__).resolve().parent


def wait_ready():
    client = requests.Session()
    client.trust_env = False
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            response = client.get("http://127.0.0.1:8080/api/method/ping",
                                  headers={"Host": "ccm-frappe.test"}, timeout=2)
            if response.status_code == 200 and response.json().get("message") == "pong":
                return
        except (requests.RequestException, ValueError):
            pass
        time.sleep(0.2)
    raise RuntimeError("Site not ready after restart; inspect private service logs")


def main():
    before = json.loads((ROOT / "processes.json").read_text())
    started = time.perf_counter()
    subprocess.run([sys.executable, str(SCRIPTS / "services.py"), "stop"], check=True)
    for port in (3307, 13000, 11000, 8000, 8080):
        with socket.socket() as connection:
            connection.settimeout(1)
            assert connection.connect_ex(("127.0.0.1", port)) != 0, f"Port {port} remained open"
    assert json.loads((ROOT / "processes.json").read_text()) == {}
    subprocess.run([sys.executable, str(SCRIPTS / "services.py"), "start"], check=True)
    wait_ready()
    after = json.loads((ROOT / "processes.json").read_text())
    assert set(before) == set(after)
    assert all(before[name] != after[name] for name in before), "Expected new process identities"
    subprocess.run([sys.executable, str(SCRIPTS / "validate_http.py"), "after"], check=True)
    subprocess.run([sys.executable, str(SCRIPTS / "validate_infrastructure.py"), "after"], check=True)
    evidence = {
        "run_id": (ROOT / "validation-run-id").read_text(),
        "status": "passed", "graceful_stop": True,
        "ports_confirmed_closed": [3307, 13000, 11000, 8000, 8080],
        "restarted_services": list(after), "all_process_identities_changed": True,
        "site_ready_with_real_http_response": True,
        "updated_document_persisted": True, "existing_api_token_survived": True,
        "password_reauthentication_passed": True,
        "wall_seconds": round(time.perf_counter() - started, 3),
    }
    (ROOT / "restart-evidence.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
