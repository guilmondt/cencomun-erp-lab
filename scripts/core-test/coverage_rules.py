"""Require named coverage and evidence revision before approving a criterion."""


def archive_evidence(out, archive):
    """Preserve all generated files before clearing stale results for a new run."""
    files = [p for p in out.iterdir() if p.is_file()]
    archive.mkdir(parents=True, exist_ok=True)
    for source in files:
        data = source.read_bytes()
        target = archive / source.name
        target.write_bytes(data)
        if target.read_bytes() != data:
            raise RuntimeError("Evidence archive verification failed: " + source.name)
    for source in files:
        source.unlink()


def apply_contract(cases, contract):
    actual = {c["case"]: dict(c) for c in cases}
    gaps = []
    for required in contract["requirements"]:
        name = required["case"]
        row = actual.get(name)
        reason = None
        if row is None:
            reason = "Mandatory case has not executed"
            row = {"case": name, "status": "UNRUN", "evidence": "reports/evidence/frappe-core/coverage.json"}
        elif row.get("coverage_revision", 1) < required["minimum_revision"]:
            reason = "Prior evidence does not include the required corrected assertions"
            row["prior_observation_status"] = row["status"]
        if reason:
            if row["status"] not in ["FAIL", "BLOCKED"]:
                row["status"] = "UNRUN"
            row["coverage_gap"] = reason
            gaps.append({"case": name, "criteria": required["criteria"], "reason": reason})
        row["criteria"] = sorted(set(row.get("criteria", []) + required["criteria"]))
        actual[name] = row
    return list(actual.values()), gaps


def criterion_status(linked):
    if not linked:
        return "UNRUN"
    for state in ["FAIL", "BLOCKED", "UNRUN"]:
        if any(row["status"] == state for row in linked):
            return state
    return "PASS" if all(row["status"] == "PASS" for row in linked) else "UNRUN"
