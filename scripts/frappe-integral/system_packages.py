"""Install pinned, checksum-verified Debian services into a user-owned prefix."""

import hashlib
import json
import os
import platform
import subprocess
import tarfile
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
REPO = Path(__file__).resolve().parents[2]


def installed_contents_match(artifact):
    process = subprocess.Popen(["dpkg-deb", "--fsys-tarfile", str(artifact)], stdout=subprocess.PIPE)
    matches = True
    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for entry in archive:
            destination = ROOT / "sysroot" / entry.name.removeprefix("./")
            if entry.isfile():
                source_hash = hashlib.file_digest(archive.extractfile(entry), "sha256").hexdigest()
                if not destination.is_file():
                    matches = False
                elif hashlib.file_digest(destination.open("rb"), "sha256").hexdigest() != source_hash:
                    matches = False
            elif entry.issym() and (not destination.is_symlink() or os.readlink(destination) != entry.linkname):
                matches = False
    assert process.wait() == 0
    return matches


def main():
    assert platform.machine() == "x86_64", "This lock targets Debian 13 amd64"
    apt = ROOT / "apt"
    for directory in ("lists/partial", "cache/archives/partial", "conf.d", "sources.d"):
        (apt / directory).mkdir(parents=True, exist_ok=True)
    (ROOT / "debs").mkdir(parents=True, exist_ok=True)
    (ROOT / "sysroot").mkdir(parents=True, exist_ok=True)
    (apt / "sources.list").write_text(
        "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main\n"
        "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://security.debian.org/debian-security trixie-security main\n"
    )
    config = {
        "Dir::Etc::parts": apt / "conf.d", "Dir::Etc::main": apt / "unused-main.conf",
        "Dir::Etc::sourcelist": apt / "sources.list", "Dir::Etc::sourceparts": apt / "sources.d",
        "Dir::State::lists": apt / "lists", "Dir::Cache": apt / "cache",
        "APT::Sandbox::User": "agent",
    }
    config_path = apt / "isolated.conf"
    config_path.write_text("".join(f'{key} "{value}";\n' for key, value in config.items()))
    environment = os.environ.copy()
    environment["APT_CONFIG"] = str(config_path)
    records = json.loads((REPO / "labs/frappe/integral/debian-packages.lock.json").read_text())
    missing = [item for item in records if not (ROOT / "debs" / item["filename"]).exists()]
    if missing:
        subprocess.run(["/usr/bin/apt-get", "update"], env=environment, check=True)
        subprocess.run(["/usr/bin/apt-get", "download",
                        *[item["package"] + "=" + item["version"] for item in missing]],
                       cwd=ROOT / "debs", env=environment, check=True)
    for item in records:
        artifact = ROOT / "debs" / item["filename"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == item["sha256"], item["package"]
        if not installed_contents_match(artifact):
            if (ROOT / "processes.json").exists() and json.loads((ROOT / "processes.json").read_text()):
                raise RuntimeError("Stop this lab's services before restoring changed system artifacts")
            subprocess.run(["dpkg-deb", "-x", str(artifact), str(ROOT / "sysroot")], check=True)
    print(f"Verified {len(records)} pinned Debian artifacts and installed contents")


if __name__ == "__main__":
    main()
