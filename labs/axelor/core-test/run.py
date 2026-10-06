#!/usr/bin/env python3
"""Execute the economic gates first; publish strict revision-two native coverage.

No database connection, expected business values are assertion-only. A missing
implementation is UNRUN, never a passing substitute for a required group.
"""
import argparse
import hashlib
import http.cookiejar
import json
import platform
import time
import urllib.parse
import urllib.request
from collections import Counter
from decimal import Decimal
from pathlib import Path

REFERENCE = "fcf690dbc58b2b2dcf8d045c49976e3613e804cf"
MANIFEST_SHA = "28496929050e7cfeea214dbf0ee5cbd589a08ab2adb60e1849877778baaf9aed"
RANK = {"PASS": 0, "UNRUN": 1, "BLOCKED": 2, "FAIL": 3}


def verify_bundle(root):
    raw = (root / "manifest.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == MANIFEST_SHA, "Fixed manifest changed"
    manifest = json.loads(raw)
    for item in manifest["files"]:
        value = (root / item["path"]).read_bytes()
        assert len(value) == item["bytes"] and hashlib.sha256(value).hexdigest() == item["sha256"], item["path"]
    required = json.loads((root / "coverage-required.json").read_bytes())
    assert required["coverage_revision"] == 2 and len(required["requirements"]) == 34
    return required


class NativeClient:
    def __init__(self, base):
        self.base = base
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.samples = []

    def request(self, path, data=None):
        headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
        for cookie in self.cookies:
            if cookie.name == "CSRF-TOKEN":
                headers["X-CSRF-Token"] = cookie.value
        raw = None if data is None else json.dumps(data).encode()
        if raw is not None:
            headers["Content-Type"] = "application/json"
        start = time.perf_counter()
        try:
            with self.opener.open(urllib.request.Request(self.base + path, raw, headers), timeout=600) as r:
                return json.loads(r.read())
        finally:
            self.samples.append({"operation": path.split("?")[0], "http_ms": round((time.perf_counter() - start) * 1000, 3)})

    def login(self):
        info = self.request("/ws/public/app/info")
        callback = urllib.parse.urlsplit(info["authentication"]["callbackUrl"])
        context = urllib.parse.urlsplit(self.base).path
        assert callback.path.startswith(context + "/callback")
        self.request(callback.path[len(context):] + "?client_name=AxelorFormClient", {"username": "admin", "password": "admin"})
        info = self.request("/ws/public/app/info")
        assert info["user"]["login"] == "admin"
        assert info["application"]["aopVersion"] == "8.2.3"

    def action(self, name, case):
        result = self.request("/ws/action", {"action": name, "model": "com.axelor.apps.base.db.Company", "data": {"context": {"case_id": case}}})
        if result.get("status") != 0:
            raise RuntimeError("Native action rejected: " + json.dumps(result)[:2500])
        for row in result.get("data", []):
            values = row.get("values", {})
            if "core_result" in values:
                return values["core_result"]
        raise RuntimeError("Native action did not return evidence: " + json.dumps(result)[:2500])


def rows_for(required):
    return [{**x, "status": "UNRUN", "observed_revision": 0,
             "reason": "Required native acceptance implementation has not run"} for x in required["requirements"]]


def criteria_for(rows, build_status):
    result = []
    for number in range(1, 15):
        attached = [r for r in rows if number in r["criteria"]]
        status = max((r["status"] for r in attached), key=RANK.get) if attached else "UNRUN"
        reason = "All attached groups must meet their minimum revision"
        if number == 2:
            status, reason = build_status, "Baseline compile/WAR/unit/strict-lock checks, separate from business parity"
        if number == 13:
            status, reason = "BLOCKED", "User deferred upgrade to an isolated copy with a separately approved target; six patch scenarios UNRUN"
        if number in (11, 12, 14) and status == "PASS":
            status, reason = "UNRUN", "Benchmark/restored independent replay additional evidence not yet executed"
        result.append({"criterion": number, "status": status, "groups": [r["case"] for r in attached], "reason": reason})
    return result


def assert_native_economics(native, expected):
    quantities = {x["code"]: Decimal(x["current_qty"]) for x in native["stock"]}
    assert [quantities[f"P{i:03}"] for i in (1, 2, 3)] == list(map(Decimal, expected["stock"])), quantities
    value = sum(Decimal(x["current_qty"]) * Decimal(x["avg_price"]) for x in native["stock"])
    assert value == Decimal(expected["stock_value"]), ("native stock valuation", value)
    assert len(native["sale_order_ids"]) == len(native["deliveries"]) == len(native["invoices"]) == 1
    assert native["deliveries"][0]["status"] == 3, native["deliveries"]
    invoice = native["invoices"][0]
    assert int(invoice["statusSelect"]) == 3, invoice
    for key, field in [("revenue", "exTaxTotal"), ("tax", "taxTotal"), ("gross", "inTaxTotal"), ("customer_balance_final", "amountRemaining")]:
        assert Decimal(invoice[field]) == Decimal(expected[key]), (field, invoice[field], expected[key])
    assert len(invoice["payments"]) == 2 and all(p["status"] == 2 for p in invoice["payments"]), invoice["payments"]
    assert sum(Decimal(p["amount"]) for p in invoice["payments"]) == Decimal(expected["gross"])
    assert Decimal(invoice["amountPaid"]) == Decimal(expected["gross"])
    balances = Counter()
    seen = set()
    for move in native["moves"]:
        assert move["id"] not in seen, "Duplicate move in export"
        seen.add(move["id"])
        assert move["status"] == 3, move
        debit = sum(Decimal(l["debit"]) for l in move["lines"])
        credit = sum(Decimal(l["credit"]) for l in move["lines"])
        assert debit == credit, ("Unbalanced native journal", move["id"])
        for line in move["lines"]:
            balances[line["account_code"]] += Decimal(line["debit"]) - Decimal(line["credit"])
            if line["account_code"] == "CCM-AR":
                assert Decimal(line["remaining"]) == 0, line
    for code, key, sign in [("COGS", "cost", 1), ("STOCK", "cost", -1), ("REVENUE", "revenue", -1),
                            ("TAX", "tax", -1), ("COMMISSION", "commission", 1), ("SHIPPING", "shipping", 1),
                            ("CASH", "upfront", 1), ("BANK", "transfer", 1)]:
        assert balances["CCM-" + code] == Decimal(expected[key]) * sign, (code, balances["CCM-" + code], expected[key])
    assert balances["CCM-AR"] == 0
    profit = -sum(balances["CCM-" + code] for code in ["REVENUE", "COGS", "COMMISSION", "SHIPPING"])
    assert profit == Decimal(expected["accounting_profit"])
    return {"stock_value": str(value), "account_balances": {k: str(v) for k, v in balances.items()}, "accounting_profit": str(profit)}


def run(base, fixtures, output):
    output.mkdir(parents=True, exist_ok=True)
    required = verify_bundle(fixtures)
    rows = rows_for(required)
    by_case = {r["case"]: r for r in rows}
    client = NativeClient(base)
    client.login()
    gates = []
    # Explicit order, regardless of the ordering of rows in coverage-required.json.
    for case in ("CO00", "TAX01-W"):
        start = time.perf_counter()
        try:
            observed = client.action("ccm-core-native-gate", case)
            # Independent new HTTP request reads durable records, after any rollback.
            native = client.action("ccm-core-native-inspect", case)
            (output / f"{case}-native-export.json").write_text(json.dumps(native, indent=2) + "\n")
            observed["committed_native_export"] = f"{case}-native-export.json"
            if observed.get("status") == "PASS":
                oracle = json.loads((fixtures / "oracle.json").read_bytes())
                observed["asserted_native_economics"] = assert_native_economics(native, oracle[case])
        except AssertionError as error:
            observed = {"case": case, "status": "FAIL", "error": str(error), "error_type": type(error).__name__}
        except Exception as error:
            observed = {"case": case, "status": "BLOCKED", "error": str(error)[:2500], "error_type": type(error).__name__}
        observed["seconds"] = round(time.perf_counter() - start, 3)
        observed["sequence"] = len(gates) + 1
        gates.append(observed)
        row = by_case[case + "-NATIVE"]
        row.update(status=observed["status"], observed_revision=1,
                   reason=observed.get("failed_stage", "native economic gate") + ": " + observed.get("error", ""), evidence=f"{case}-gate.json")
        (output / f"{case}-gate.json").write_text(json.dumps(observed, indent=2) + "\n")
        # Persist and publish impediment before expanding independent checks.
        message = json.dumps(observed, ensure_ascii=True).replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
        print(f"::notice title=Core gate {case}::{message[:3800]}", flush=True)
    (output / "gate-impediments.json").write_text(json.dumps(gates, indent=2) + "\n")
    results = {"reference": REFERENCE, "coverage_revision": 2,
               "groups": rows, "criteria": criteria_for(rows, "PASS"),
               "counts": dict(Counter(r["status"] for r in rows)),
               "patch_scenarios": {"status": "UNRUN", "count": 6},
               "scope": "Actual native gates. Policy unit tests do not mark native groups PASS."}
    (output / "coverage.json").write_text(json.dumps(results, indent=2) + "\n")
    (output / "metrics.json").write_text(json.dumps({"gates": [{"case": g["case"], "seconds": g["seconds"], "status": g["status"]} for g in gates],
                                                   "http_samples": client.samples, "platform": platform.platform(),
                                                   "benchmark": "UNRUN", "note": "Gate timings are not the required 1000-sample benchmark"}, indent=2) + "\n")
    print("::notice title=Core coverage::" + json.dumps({"reference": REFERENCE, "groups": results["counts"], "criteria": dict(Counter(r["status"] for r in results["criteria"]))}), flush=True)
    return 0 if all(r["status"] == "PASS" for r in rows) else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.base, args.fixtures, args.output))
