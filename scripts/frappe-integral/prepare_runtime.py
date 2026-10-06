"""Prepare the tested local configuration without replacing user edits/data."""

import subprocess
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
REPO = Path(__file__).resolve().parents[2]


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    ROOT.chmod(0o700)
    for directory in ("logs", "nginx", "nginx/client_temp", "nginx/proxy_temp",
                      "nginx/fastcgi_temp", "nginx/uwsgi_temp", "nginx/scgi_temp"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    for name in ("mariadb.cnf", "nginx.conf"):
        expected = (REPO / f"labs/frappe/integral/{name}.template").read_text().replace("@ROOT@", str(ROOT))
        path = ROOT / name
        if path.exists() and path.read_text() != expected:
            raise RuntimeError(f"Preserving changed local configuration: review {path}")
        if not path.exists():
            path.write_text(expected)
    if not (ROOT / "mariadb-data/mysql").exists():
        subprocess.run([str(ROOT / "sysroot/usr/bin/mariadb-install-db"), "--no-defaults",
                        f"--basedir={ROOT / 'sysroot/usr'}", f"--datadir={ROOT / 'mariadb-data'}",
                        "--auth-root-authentication-method=socket", "--auth-root-socket-user=agent",
                        "--skip-test-db"], check=True)
    print("Local service configuration and existing database preserved")


if __name__ == "__main__":
    main()
