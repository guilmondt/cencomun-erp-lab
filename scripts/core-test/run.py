"""End-to-end isolated Core Test runner; business groups continue independently."""

import json, os, subprocess, time, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/workspace/.local/frappe-integral")
BENCH = ROOT / "bench"
PYTHON = str(BENCH / "env/bin/python")
OUT = REPO / "reports/evidence/frappe-core"
OUT.mkdir(parents=True, exist_ok=True)
assert (
    subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=REPO, text=True
    ).strip()
    == "lab/frappe-baseline"
)
RUN = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
STEPS = []


def step(name, args, required=True, cwd=REPO):
    started = time.monotonic()
    log = ROOT / ("logs/core-" + name + ".log")
    with log.open("w") as f:
        r = subprocess.run(args, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    STEPS.append(
        {
            "step": name,
            "exit_code": r.returncode,
            "seconds": round(time.monotonic() - started, 3),
            "private_log": log.name,
        }
    )
    (OUT / "commands.json").write_text(
        json.dumps({"run": RUN, "steps": STEPS}, indent=2) + "\n"
    )
    print(name, r.returncode, flush=True)
    if required and r.returncode:
        raise RuntimeError(
            name + " failed; inspect sanitized log and independent stages"
        )
    return r.returncode


def site(script):
    return [
        PYTHON,
        str(REPO / "scripts/core-test/site_command.py"),
        str(REPO / ("scripts/core-test/" + script + ".py")),
    ]


step("preflight", ["bash", "scripts/preflight.sh"])
step("install-tools", [PYTHON, "scripts/core-test/install_tools.py"])
step(
    "test-dependencies",
    [
        "uv",
        "pip",
        "install",
        "--python",
        PYTHON,
        "-r",
        "labs/frappe/integral/core-test-dependencies.lock",
    ],
)
step("services-start", [PYTHON, "scripts/frappe-integral/services.py", "start"])
step("prepare-site", [PYTHON, "scripts/core-test/prepare_site.py"])
step("http-stop", [PYTHON, "scripts/core-test/http_services.py", "stop"])
# Preserve previous evidence and synthetic consumer DB before resetting the marked lab.
archive = OUT / "runs" / RUN
archive.mkdir(parents=True, exist_ok=True)
for f in OUT.iterdir():
    if f.is_file():
        (archive / f.name).write_bytes(f.read_bytes())
consumer = ROOT / "core-consumer.sqlite"
if consumer.exists():
    hist = ROOT / "core-consumer-history"
    hist.mkdir(exist_ok=True)
    consumer.rename(hist / (RUN + ".sqlite"))
(ROOT / "core-consumer-fail").unlink(missing_ok=True)
step("restore-checkpoint", [PYTHON, "scripts/core-test/reset_lab.py"])
step("disable-metrics", site("disable_metrics"))
step("seed", site("seed"))
step("business", site("business_cases"), False)
step("finance", site("finance_cases"), False)
step("http-setup", site("http_setup"))
step(
    "web-worker-stop",
    [PYTHON, "scripts/frappe-integral/services.py", "stop", "web", "worker"],
)
step(
    "web-worker-start",
    [PYTHON, "scripts/frappe-integral/services.py", "start", "web", "worker"],
)
step("http-start", [PYTHON, "scripts/core-test/http_services.py", "start"])
step("http", [PYTHON, "scripts/core-test/http_cases.py"], False)
step("recovery", [PYTHON, "scripts/core-test/recovery_cases.py"], False)
step("audit", site("audit_cases"), False)
step("reproducibility", [PYTHON, "scripts/core-test/clone_replay.py"], False)
step("benchmark-load", site("benchmark_setup"), False)
step(
    "benchmark-web-stop", [PYTHON, "scripts/frappe-integral/services.py", "stop", "web"]
)
step(
    "benchmark-web-start",
    [PYTHON, "scripts/frappe-integral/services.py", "start", "web"],
)
step("benchmark", [PYTHON, "scripts/core-test/benchmark.py"], False)
step("metrics-off", site("disable_metrics"))
step(
    "registration",
    [PYTHON, "-m", "unittest", "discover", "-s", "labs/frappe/tests", "-v"],
    False,
)
step("guardrails", ["bash", "scripts/verify-repo.sh"], False)
step("diff-check", ["git", "diff", "--check"], False)
step("build", [PYTHON, "scripts/core-test/build.py"], False)
step("publish", [PYTHON, "scripts/core-test/publish.py"], False)
