"""Install the pinned backup client in a separate user-owned prefix."""

import hashlib, json, os, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/workspace/.local/frappe-integral")
lock = json.loads((REPO / "labs/frappe/integral/core-tools.lock.json").read_text())
artifact = ROOT / "debs" / lock["filename"]
environment = dict(os.environ)
environment["APT_CONFIG"] = str(ROOT / "apt/isolated.conf")
if not artifact.exists():
    subprocess.run(["/usr/bin/apt-get", "update"], env=environment, check=True)
    subprocess.run(
        ["/usr/bin/apt-get", "download", lock["package"] + "=" + lock["version"]],
        env=environment,
        cwd=ROOT / "debs",
        check=True,
    )
assert hashlib.sha256(artifact.read_bytes()).hexdigest() == lock["sha256"]
subprocess.run(["dpkg-deb", "-x", str(artifact), str(ROOT / "core-tools")], check=True)
print("Pinned MariaDB backup client verified and installed separately.")
