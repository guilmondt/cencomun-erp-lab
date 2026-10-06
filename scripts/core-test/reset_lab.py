"""Explicit recovery of ONLY ccm-core.test from the immutable pre-business backup.

Always backs up current synthetic state first. Never drops another site/database.
"""

import json, subprocess, hashlib
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
BENCH = ROOT / "bench"
SITE = "ccm-core.test"
config = json.loads((BENCH / "sites" / SITE / "site_config.json").read_text())
assert (
    config["db_name"] == "ccm_core_lab"
    and (ROOT / "core-site-created").read_text().strip() == SITE
)
backups = BENCH / "sites" / SITE / "private/backups"
checkpoint = ROOT / "core-empty-checkpoint.json"
private = json.loads((ROOT / "core-private.json").read_text())
bootstrap = json.loads((ROOT / "secrets.json").read_text())


def run(args, label):
    with (ROOT / ("logs/core-" + label + ".log")).open("w") as f:
        r = subprocess.run(
            [str(ROOT / "bench-tools/bin/bench"), "--site", SITE] + args,
            cwd=BENCH,
            stdout=f,
            stderr=subprocess.STDOUT,
        )
    print(label, r.returncode, flush=True)
    if r.returncode:
        raise SystemExit(r.returncode)


run(["backup", "--with-files"], "pre-reset-backup")
if not checkpoint.exists():
    old = sorted(backups.glob("*-database.sql.gz"))[0]
    checkpoint.write_text(
        json.dumps(
            {"path": str(old), "sha256": hashlib.sha256(old.read_bytes()).hexdigest()}
        )
    )
cp = json.loads(checkpoint.read_text())
assert hashlib.sha256(Path(cp["path"]).read_bytes()).hexdigest() == cp["sha256"]
run(
    [
        "restore",
        cp["path"],
        "--force",
        "--db-root-username",
        "ccm_bootstrap",
        "--db-root-password",
        bootstrap["bootstrap_password"],
        "--admin-password",
        private["admin_password"],
    ],
    "restore-checkpoint",
)
run(["migrate"], "migrate")
print("Restored the isolated LAB database from its verified pre-business checkpoint.")
