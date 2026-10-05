"""Recover a separate site and replay the frozen native business suites there.

Restores ONLY the separately marked ccm-core-recovery.test synthetic database.
"""

import hashlib, json, os, subprocess, time
from pathlib import Path

REPO = Path("/workspace/cencomun-erp-lab")
ROOT = Path("/workspace/.local/frappe-integral")
BENCH = ROOT / "bench"
SITE = "ccm-core-recovery.test"
OUT = REPO / "reports/evidence/frappe-core"
OUT.mkdir(parents=True, exist_ok=True)
private = json.loads((ROOT / "core-private.json").read_text())
bootstrap = json.loads((ROOT / "secrets.json").read_text())
source = json.loads((BENCH / "sites/ccm-core.test/site_config.json").read_text())
checkpoint = json.loads((ROOT / "core-empty-checkpoint.json").read_text())
commands = []


def run(args, label, cwd=REPO, env=None):
    start = time.monotonic()
    with (ROOT / ("logs/core-" + label + ".log")).open("w") as f:
        r = subprocess.run(args, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT)
    commands.append(
        {
            "step": label,
            "exit_code": r.returncode,
            "seconds": round(time.monotonic() - start, 3),
        }
    )
    print(label, r.returncode, flush=True)
    if r.returncode:
        raise RuntimeError(label + " exit " + str(r.returncode))


bench = [str(ROOT / "bench-tools/bin/bench")]
marker = ROOT / "core-recovery-site-created"
if not marker.exists():
    assert not (BENCH / "sites" / SITE).exists(), (
        "Unmarked recovery site must be inspected"
    )
    run(
        bench
        + [
            "new-site",
            SITE,
            "--db-name",
            "ccm_core_recovery",
            "--db-host",
            "127.0.0.1",
            "--db-port",
            "3307",
            "--db-socket",
            str(ROOT / "mariadb.sock"),
            "--db-root-username",
            "ccm_bootstrap",
            "--db-root-password",
            bootstrap["bootstrap_password"],
            "--admin-password",
            private["admin_password"],
        ],
        "recovery-new-site",
        BENCH,
    )
    marker.write_text(SITE + "\n")
config_path = BENCH / "sites" / SITE / "site_config.json"
conf = json.loads(config_path.read_text())
assert conf["db_name"] == "ccm_core_recovery"
# Recovery site must use the source encryption key to decrypt restored synthetic user keys.
for key in [
    "encryption_key",
    "ccm_lab_enabled",
    "ccm_company",
    "ccm_accounts",
    "ccm_bank_account",
]:
    if key in source:
        conf[key] = source[key]
config_path.write_text(json.dumps(conf))
config_path.chmod(0o600)
assert (
    hashlib.sha256(Path(checkpoint["path"]).read_bytes()).hexdigest()
    == checkpoint["sha256"]
)
run(
    bench
    + [
        "--site",
        SITE,
        "restore",
        checkpoint["path"],
        "--force",
        "--db-root-username",
        "ccm_bootstrap",
        "--db-root-password",
        bootstrap["bootstrap_password"],
        "--admin-password",
        private["admin_password"],
    ],
    "recovery-restore",
    BENCH,
)
run(bench + ["--site", SITE, "migrate"], "recovery-migrate", BENCH)
environment = dict(os.environ)
environment["CCM_CORE_SITE"] = SITE
original = {
    name: (OUT / (name + ".json")).read_bytes() for name in ["business", "finance"]
}
try:
    for script in ["seed", "business_cases", "finance_cases"]:
        run(
            [
                str(BENCH / "env/bin/python"),
                str(REPO / "scripts/core-test/site_command.py"),
                str(REPO / ("scripts/core-test/" + script + ".py")),
            ],
            "recovery-replay-" + script,
            env=environment,
        )
    for name in ["business", "finance"]:
        result = json.loads((OUT / (name + ".json")).read_text())
        assert all(c["status"] == "PASS" for c in result["cases"]), name
        (OUT / ("replayed-" + name + ".json")).write_text(
            json.dumps(result, indent=2) + "\n"
        )
finally:
    for name, content in original.items():
        (OUT / (name + ".json")).write_bytes(content)
# Run the official platform utility suite in the recovery site, not in the measured site.
run(
    bench + ["--site", SITE, "set-config", "allow_tests", "true"],
    "platform-enable-tests",
    BENCH,
)
run(
    bench
    + [
        "--site",
        SITE,
        "run-tests",
        "--module",
        "frappe.tests.test_utils",
        "--skip-before-tests",
        "--test-category",
        "unit",
    ],
    "platform-utils",
    BENCH,
)
(OUT / "reproducibility.json").write_text(
    json.dumps(
        {
            "status": "PASS",
            "source_checkpoint_sha256": checkpoint["sha256"],
            "target_site": SITE,
            "target_database": "ccm_core_recovery",
            "suites_replayed": ["business", "finance"],
            "commands": commands,
            "native_core_suite": "frappe.tests.test_utils (unit category only)",
            "production_touched": False,
        },
        indent=2,
    )
    + "\n"
)
