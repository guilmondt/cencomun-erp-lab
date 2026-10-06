"""Collect only explicit secret-free outcomes from one completed validation run."""

import datetime
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
REPO = Path(__file__).resolve().parents[2]


def git(path, *arguments):
    return subprocess.run(["git", "-C", str(path), *arguments], check=True,
                          text=True, capture_output=True).stdout.strip()


def main(target):
    run_id = (ROOT / "validation-run-id").read_text()
    outcomes = {}
    for name in ("http-before", "http-after", "infrastructure-before", "infrastructure-after", "restart-evidence"):
        value = json.loads((ROOT / (name + ".json")).read_text())
        assert value["run_id"] == run_id, "Mixed validation runs"
        outcomes[name] = value
    for phase, expected in (("before", 17), ("after", 14)):
        result = outcomes["http-" + phase]
        assert result["all_executed_checks_passed"] and len(result["checks"]) == expected
        assert all(check["status"] == "passed" for check in result["checks"])
        result = outcomes["infrastructure-" + phase]
        assert len(result["checks"]) == 4 and all(check["status"] == "passed" for check in result["checks"])
    assert outcomes["restart-evidence"]["status"] == "passed"
    assert git(REPO, "branch", "--show-current") == "lab/frappe-baseline"
    upstream = {}
    for name, expected in (("frappe", "97a5dd93ca5883bcc9c4ef9834120c5cba397b67"),
                           ("erpnext", "fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba")):
        checkout = ROOT / "bench/apps" / name
        assert git(checkout, "rev-parse", "HEAD") == expected
        assert git(checkout, "status", "--porcelain") == "", "Upstream checkout changed"
        upstream[name] = {"commit": expected, "tracked_and_untracked_status": "clean"}
    log = (ROOT / "logs/validation-final.log").read_text()
    assert "Ran 5 tests" in log and "\nOK\n" in log
    files = [*sorted((REPO / "scripts/frappe-integral").glob("*.py")),
             *sorted((REPO / "scripts/frappe-integral").glob("*.sh")),
             *sorted((REPO / "labs/frappe/integral").glob("*")), REPO / "versions.lock"]
    source_hashes = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in files if path.is_file()}
    evidence = {
        "run_id": run_id, "recorded_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "branch": "lab/frappe-baseline", "repository_base_commit": git(REPO, "rev-parse", "HEAD"),
        "scope": "Real-site installation/authentication/API/persistence/graceful restart with fictitious data",
        "bootstrap": json.loads((ROOT / "bootstrap-evidence.json").read_text()),
        "upstream": upstream, "functional_checks_passed": 39, "functional_checks_failed": 0,
        "functional_checks_skipped": 0, "skeleton_tests_passed": 5,
        "install_refresh": "passed, including frozen frontend and Python dependency locks",
        "outcomes": outcomes, "runner_and_lock_sha256": source_hashes,
        "limitations": [
            "Debian 13 amd64 cloud machine; independent fresh-machine restore not tested",
            "Synthetic System Manager account; Core Test/business correctness/full upstream suite not tested",
            "Graceful restart only; crash/power failure/backup restore not tested",
            "Loopback HTTP; no public deployment/TLS/browser UI/end-to-end realtime authorization test",
            "Contact/license metadata remain placeholders; no production data or production credentials",
            "CI guardrails are separate from these live-machine functional checks",
        ],
    }
    serialized = json.dumps(evidence, indent=2) + "\n"
    private = json.loads((ROOT / "secrets.json").read_text())
    site = json.loads((ROOT / "bench/sites/ccm-frappe.test/site_config.json").read_text())
    for key in ("db_password", "encryption_key"):
        if site.get(key):
            private[key] = site[key]
    for name, value in private.items():
        if name != "validation_email" and value:
            assert value not in serialized, "Refusing to publish an authentication value"
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialized)
    print(f"Evidence: {target}; run {run_id}; 39 functional checks and 5 skeleton tests passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(REPO / "reports/generated/frappe-integral/evidence.json"))
    main(parser.parse_args().output)
