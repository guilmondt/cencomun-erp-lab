"""Verify real Redis/worker/socket services through the Frappe runtime."""

import argparse
import json
import os
import time
from pathlib import Path

import frappe
import redis
import requests

ROOT = Path("/workspace/.local/frappe-integral")


def main(phase):
    results = []
    os.chdir(ROOT / "bench/sites")
    frappe.init(site="ccm-frappe.test", sites_path=str(ROOT / "bench/sites"))
    frappe.connect()
    try:
        frappe.set_user("Administrator")
        for key in ("redis_cache", "redis_queue"):
            connection = redis.Redis.from_url(frappe.conf[key])
            assert connection.ping()
            version = connection.info("server")["redis_version"]
            assert version == "8.0.2", version
            results.append({"check": key + "_ping", "status": "passed", "redis_version": version})
        job = frappe.enqueue("frappe.utils.data.cint", s="41", queue="short",
                             job_name="ccm_synthetic_integral_" + phase)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            status = job.get_status(refresh=True)
            if status.value in ("finished", "failed"):
                break
            time.sleep(0.2)
        assert status.value == "finished", str(status)
        assert job.result == 41, "Unexpected worker result"
        results.append({"check": "frappe_redis_worker_job", "status": "passed", "result": 41})
        client = requests.Session()
        client.trust_env = False
        response = client.get("http://127.0.0.1:8080/socket.io/",
                              params={"EIO": 4, "transport": "polling"},
                              headers={"Host": "ccm-frappe.test"}, timeout=15)
        assert response.status_code == 200 and response.text.startswith("0{"), response.status_code
        results.append({"check": "socketio_proxy_handshake", "status": "passed", "http_status": 200})
    finally:
        frappe.destroy()
        (ROOT / f"infrastructure-{phase}.json").write_text(json.dumps({
            "run_id": (ROOT / "validation-run-id").read_text(), "phase": phase,
            "checks": results,
        }, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["before", "after"])
    main(parser.parse_args().phase)
