"""Create an isolated LAB-only site without disclosing private credentials."""

import json
import secrets
import subprocess
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
BENCH = ROOT / "bench"
SITE = "ccm-core.test"
PRIVATE = ROOT / "core-private.json"
data = json.loads(PRIVATE.read_text()) if PRIVATE.exists() else {}
data.setdefault("admin_password", secrets.token_urlsafe(32))
PRIVATE.write_text(json.dumps(data))
PRIVATE.chmod(0o600)
bootstrap = json.loads((ROOT / "secrets.json").read_text())
marker = ROOT / "core-site-created"
if not marker.exists():
    if (BENCH / "sites" / SITE).exists():
        raise SystemExit(
            "Existing unmarked core site: inspect it; never force/drop it."
        )
    command = [
        str(ROOT / "bench-tools/bin/bench"),
        "new-site",
        SITE,
        "--db-name",
        "ccm_core_lab",
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
        data["admin_password"],
    ]
    with (ROOT / "logs/core-new-site.log").open("w") as output:
        result = subprocess.run(
            command, cwd=BENCH, stdout=output, stderr=subprocess.STDOUT
        )
    print("Core site creation:", result.returncode)
    if result.returncode:
        raise SystemExit(result.returncode)
    marker.write_text(SITE + "\n")
for app in ["erpnext", "cencomun_erp"]:
    with (ROOT / f"logs/core-install-{app}.log").open("w") as output:
        result = subprocess.run(
            [str(ROOT / "bench-tools/bin/bench"), "--site", SITE, "install-app", app],
            cwd=BENCH,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
    print("Core install", app, result.returncode)
    if result.returncode:
        raise SystemExit(result.returncode)
