"""Create only the isolated synthetic site; never print local passwords."""

import json
import secrets
import subprocess
import time
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
SITE = ROOT / "bench/sites/ccm-frappe.test"
PRIVATE = ROOT / "secrets.json"


def credentials():
    data = json.loads(PRIVATE.read_text()) if PRIVATE.exists() else {}
    for name in ("admin_password", "user_password", "bootstrap_password"):
        data.setdefault(name, secrets.token_urlsafe(32))
    data.setdefault("validation_email", "validation@example.invalid")
    PRIVATE.write_text(json.dumps(data))
    PRIVATE.chmod(0o600)
    return data


def main():
    data = credentials()
    if (ROOT / "site-created").exists():
        print("Synthetic site already created; validate it rather than recreating it.")
        return
    # Database setup account only; application documents are never written through SQL.
    sql = (
        "CREATE USER IF NOT EXISTS 'ccm_bootstrap'@'localhost' IDENTIFIED BY '"
        + data["bootstrap_password"]
        + "'; GRANT ALL PRIVILEGES ON *.* TO 'ccm_bootstrap'@'localhost' WITH GRANT OPTION;"
    )
    subprocess.run([str(ROOT / "sysroot/usr/bin/mariadb"), "--no-defaults",
                    f"--socket={ROOT / 'mariadb.sock'}", "-u", "agent"],
                   input=sql, text=True, check=True, stdout=subprocess.DEVNULL)
    if SITE.exists():
        # Preserve the preceding failed attempt; never force/drop a populated site.
        SITE.rename(ROOT / f"site-creation-attempt-{time.time_ns()}")
    command = [str(ROOT / "bench-tools/bin/bench"), "new-site", "ccm-frappe.test",
               "--db-name", "ccm_frappe_integral", "--db-host", "127.0.0.1",
               "--db-port", "3307", "--db-socket", str(ROOT / "mariadb.sock"),
               "--db-root-username", "ccm_bootstrap", "--db-root-password",
               data["bootstrap_password"], "--admin-password", data["admin_password"],
               "--set-default"]
    with (ROOT / "logs/new-site.log").open("w") as output:
        result = subprocess.run(command, cwd=ROOT / "bench", stdout=output,
                                stderr=subprocess.STDOUT)
    print("Site creation exit code:", result.returncode)
    if result.returncode:
        raise SystemExit(result.returncode)
    (ROOT / "site-created").write_text("ccm-frappe.test\n")


if __name__ == "__main__":
    main()
