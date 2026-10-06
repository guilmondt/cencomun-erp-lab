#!/usr/bin/env python3
"""Verify the real ERP address repository save before Core gates and restart.

This fixture prerequisite never counts as an economic gate or complete Core group.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core-test"))
from run import NativeClient, REFERENCE


def assert_address(prepared, committed):
    assert prepared["address_id"] == committed["address_id"] > 0
    assert "AddressBaseRepository" in prepared["repository"], prepared
    assert committed["read_boundary"] == "separate-http-after-address-commit"
    assert committed["street"] == "1 Synthetic LAB Street"
    assert committed["city"] == "Synthetic LAB City" and committed["zip"] == "00000"
    assert committed["formatted_full_name"] == "Synthetic LAB preflight\n1 Synthetic LAB Street\nSynthetic LAB City 00000"
    assert committed["full_name"] == "SYNTHETIC LAB PREFLIGHT 1 SYNTHETIC LAB STREET SYNTHETIC LAB CITY 00000"
    lines = committed["lines"]
    assert len(lines) == 5 and {line["field"] for line in lines} == {"floor", "streetName", "postBox", "city", "zip"}
    assert {line["field"] for line in lines if line["required"]} == {"streetName", "city", "zip"}
    assert all(line["id"] > 0 and line["field_id"] > 0 and line["model"] == "com.axelor.apps.base.db.Address"
        and line["template_id"] == committed["template_id"] > 0 for line in lines)


def preflight(base, output):
    client = NativeClient(base)
    result = {"scope": "native address fixture prerequisite, not a Core group", "reference": REFERENCE,
        "lab_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[3], text=True).strip()}
    started = time.perf_counter()
    status = 1
    try:
        client.login()
        result["prepared"] = client.action("ccm-core-address-preflight", "ADDRESS")
        result["committed"] = client.action("ccm-core-address-inspect", "ADDRESS")
        assert_address(result["prepared"], result["committed"])
        # Replay the fixture, then another post-commit read: no duplicate address or template.
        replay = client.action("ccm-core-address-preflight", "ADDRESS")
        reloaded = client.action("ccm-core-address-inspect", "ADDRESS")
        assert_address(replay, reloaded)
        assert reloaded == result["committed"], "Fixture replay changed committed native address"
        result.update(status="PASS", replay_identical=True)
        status = 0
    except Exception as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error)[:1200])
    result["seconds"] = round(time.perf_counter() - started, 3)
    result["http_samples"] = client.samples
    Path(output).write_text(json.dumps(result, indent=2) + "\n")
    # Compact evidence survives the log boundary; detailed actual records remain in the artifact.
    print("::notice title=Native address preflight::" + json.dumps({k: result[k] for k in result if k != "http_samples"}))
    return status


if __name__ == "__main__":
    raise SystemExit(preflight(sys.argv[1], sys.argv[2]))
