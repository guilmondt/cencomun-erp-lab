#!/usr/bin/env python3
"""Attest actual current-run builds/upstream source checks and finalize criteria."""
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from run import criteria_for, verified_build_status, review_native_fx

BASELINE = "e0190090fd137576ce273e350d7ce6686d66baf9"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def baseline_pin_blob(repo):
    # Missing history is an error, not permission to attest the current file against itself.
    git(repo, "cat-file", "-e", BASELINE + "^{commit}")
    return git(repo, "show", BASELINE + ":versions.lock")


def finalize(repo, host, output):
    diffs = {}
    for name, root in [("host", host), ("aos", host / "modules/axelor-open-suite")]:
        diffs[name] = subprocess.run(["git", "-C", str(root), "diff", "HEAD", "--exit-code"], capture_output=True).returncode
    suites = {}
    paths = [("CencomunModuleTest", repo / "labs/axelor/cencomun-baseline/build/test-results/test/TEST-com.cencomun.baseline.module.CencomunModuleTest.xml"),
             ("MoneyPolicyTest", repo / "labs/axelor/cencomun-baseline/build/test-results/test/TEST-com.cencomun.core.MoneyPolicyTest.xml"),
             ("NativeAddressTemplateTest", repo / "labs/axelor/cencomun-baseline/build/full/test-results/test/TEST-com.cencomun.core.NativeAddressTemplateTest.xml"),
             ("NativePermissionFilterTest", repo / "labs/axelor/cencomun-baseline/build/full/test-results/test/TEST-com.cencomun.core.NativePermissionFilterTest.xml"),
             ("NativeInvoiceRuntimeTest", repo / "labs/axelor/cencomun-baseline/build/full/test-results/test/TEST-com.cencomun.core.NativeInvoiceRuntimeTest.xml"),
             ("TestTaxNumberHelper", host / "modules/axelor-open-suite/axelor-base/build/test-results/test/TEST-com.axelor.apps.base.service.partner.registrationnumber.TestTaxNumberHelper.xml")]
    for name, path in paths:
        suite = ET.parse(path).getroot()
        suites[name] = {k: int(suite.get(k)) for k in ["tests", "failures", "errors", "skipped"]}
    wars = list((host / "build/libs").glob("*.war"))
    assert len(wars) == 1
    proof = {"lab_commit": git(repo, "rev-parse", "HEAD").decode().strip(),
             "host_commit": git(host, "rev-parse", "HEAD").decode().strip(),
             "aos_commit": git(host / "modules/axelor-open-suite", "rev-parse", "HEAD").decode().strip(),
             "upstream_diff_exit_codes": diffs,
             "baseline_pin_blob_sha256": hashlib.sha256((repo / "versions.lock").read_bytes()).hexdigest(),
             "expected_baseline_pin_blob_sha256": hashlib.sha256(baseline_pin_blob(repo)).hexdigest(),
             "suites": suites, "war_sha256": hashlib.sha256(wars[0].read_bytes()).hexdigest()}
    (output / "build-evidence.json").write_text(json.dumps(proof, indent=2) + "\n")
    print("::notice title=Core build attestation::" + json.dumps(proof))
    coverage = json.loads((output / "coverage.json").read_text())
    fx = next(r for r in coverage["groups"] if r["case"] == "FX01-03-MONEY01-03")
    fx_path = output / "FX01-03-MONEY01-03.json"
    review_native_fx(fx, json.loads(fx_path.read_text()) if fx_path.exists() else {},
        json.loads((repo / "fixtures/ccm-core-v1/fx.json").read_bytes()))
    coverage["counts"] = dict(Counter(r["status"] for r in coverage["groups"]))
    coverage["criteria"] = criteria_for(coverage["groups"], proof)
    coverage["build_evidence"] = "build-evidence.json"
    (output / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    print("::notice title=Core verified coverage::" + json.dumps({"groups": coverage["counts"], "criteria": dict(Counter(c["status"] for c in coverage["criteria"])), "upstream_diff_exit_codes": diffs, "build": verified_build_status(proof)}))


if __name__ == "__main__":
    finalize(*map(Path, sys.argv[1:]))
