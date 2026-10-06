#!/usr/bin/env python3
"""Recover only structured, public Core notices from a downloaded Actions log.

This is a secondary evidence source when a ZIP is unavailable. Missing notices
remain UNRUN; never infer native success from a build or an absent exception.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from run import REFERENCE, criteria_for, rows_for, verify_bundle


def extract(log, output, run_id, commit, fixtures):
    output.mkdir(parents=True, exist_ok=True)
    objects = []
    decoder = json.JSONDecoder()
    for line in log.read_text(errors="replace").splitlines():
        if "##[notice]" not in line:
            continue
        value = line.split("##[notice]", 1)[1].lstrip()
        if not value.startswith("{"):
            continue
        try:
            item, end = decoder.raw_decode(value)
        except json.JSONDecodeError:
            continue
        if value[end:].strip():
            continue  # Truncated or mixed output never establishes a result.
        objects.append(item)
    rows = rows_for(verify_bundle(fixtures))
    by_case = {r["case"]: r for r in rows}
    gates, exports, independent = {}, {}, {}
    product_steps, search_steps = [], []
    proof = None
    for item in objects:
        case = item.get("case")
        if case in ("warranty", "disabled-price-retained") and "persisted" in item:
            product_steps.append(item)
        if case == "SEARCH01-04-NATIVE" and "step" in item:
            search_steps.append(item["step"])
        if "lab_commit" in item and "upstream_diff_exit_codes" in item and "suites" in item:
            assert item["lab_commit"] == commit, "Build proof belongs to another commit"
            proof = item
        if case in ("CO00", "TAX01-W") and "section" in item and "records" in item:
            exports.setdefault(case, {"case": case})[item["section"]] = item["records"]
        if case in ("CO00", "TAX01-W") and "sequences" in item:
            (output / f"{case}-committed-sequences.json").write_text(json.dumps(item, indent=2) + "\n")
        # The first runner fallback omitted top-level reference metadata. Its
        # complete preparation error still contains the verified native reference.
        # Recognize only that explicit legacy failure; never infer missing success.
        legacy_preparation_failure = (item.get("reference") is None and item.get("status") == "FAIL"
            and "Fixture preparation failed" in item.get("error", "")
            and ("'reference': '" + REFERENCE + "'") in item.get("error", ""))
        if case in ("CO00", "TAX01-W") and (item.get("reference") == REFERENCE or legacy_preparation_failure) and "status" in item:
            if legacy_preparation_failure:
                item["reference_evidence"] = "Exact pinned reference explicitly present in the complete native preparation error; legacy runner omitted top-level reference"
            gates[case] = item
            by_case[case + "-NATIVE"].update(status="UNRUN" if item["status"] == "PASS" else item["status"],
                observed_revision=1, complete=False, partial_gate_status=item["status"],
                reason=item.get("failed_stage", "Economic administrator gate; complete subcases pending"), evidence=f"{case}-gate.json")
        if case in ("PROD01-04", "SEARCH01-04-NATIVE") and "status" in item and item.get("reference") == REFERENCE:
            independent[case] = item
            by_case[case].update(status=item["status"], observed_revision=item["revision"], complete=item["complete"],
                reason=item.get("error", "Executed native independent case"), evidence=f"{case}.json")
    for case, item in gates.items():
        (output / f"{case}-gate.json").write_text(json.dumps(item, indent=2) + "\n")
    for case, item in exports.items():
        (output / f"{case}-native-export.json").write_text(json.dumps(item, indent=2) + "\n")
    for case, item in independent.items():
        item["steps"] = product_steps if case == "PROD01-04" else search_steps
        if item["status"] == "PASS":
            complete_notices = len(item["steps"]) == (7 if case == "PROD01-04" else 11)
            if not complete_notices:
                by_case[case].update(status="UNRUN", complete=False,
                    reason="PASS notice present but detailed persistence/query notices are incomplete; inspect full artifact")
        (output / f"{case}.json").write_text(json.dumps(item, indent=2) + "\n")
    if proof:
        (output / "build-evidence.json").write_text(json.dumps(proof, indent=2) + "\n")
    results = {"source": "complete structured Actions log notices; ZIP availability tracked separately",
        "run_id": run_id, "lab_commit": commit, "reference": REFERENCE, "coverage_revision": 2,
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "groups": rows, "counts": dict(Counter(r["status"] for r in rows)), "criteria": criteria_for(rows, proof),
        "patch_scenarios": {"status": "UNRUN", "count": 6},
        "limitations": "No missing notice is inferred. Economic gates retain incomplete role/state/atomicity coverage. Full metrics/recovery evidence require their actual result files."}
    (output / "coverage.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--fixtures", required=True, type=Path)
    args = parser.parse_args()
    result = extract(args.log, args.output, args.run_id, args.commit, args.fixtures)
    print(json.dumps({"groups": result["counts"], "criteria": dict(Counter(r["status"] for r in result["criteria"]))}))
