#!/usr/bin/env python3
"""Execute the economic gates first; publish strict revision-two native coverage.

No database connection, expected business values are assertion-only. A missing
implementation is UNRUN, never a passing substitute for a required group.
"""
import argparse
import hashlib
import http.cookiejar
import json
import os
import platform
import shutil
import time
import urllib.parse
import urllib.request
import urllib.error
from collections import Counter
from decimal import Decimal
from pathlib import Path

REFERENCE = "fcf690dbc58b2b2dcf8d045c49976e3613e804cf"
MANIFEST_SHA = "28496929050e7cfeea214dbf0ee5cbd589a08ab2adb60e1849877778baaf9aed"
RANK = {"PASS": 0, "UNRUN": 1, "BLOCKED": 2, "FAIL": 3}


def exception_status(error):
    # API/configuration incompatibilities are test defects; unavailable transport
    # is a blocker. A native HTTP error is not automatically an environment issue.
    if isinstance(error, urllib.error.HTTPError):
        return "FAIL"
    return "BLOCKED" if isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError)) else "FAIL"


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

    def login(self, username="admin", password="admin"):
        info = self.request("/ws/public/app/info")
        callback = urllib.parse.urlsplit(info["authentication"]["callbackUrl"])
        context = urllib.parse.urlsplit(self.base).path
        assert callback.path.startswith(context + "/callback")
        self.request(callback.path[len(context):] + "?client_name=AxelorFormClient", {"username": username, "password": password})
        info = self.request("/ws/public/app/info")
        assert info["user"]["login"] == username
        assert info["application"]["aopVersion"] == "8.2.3"

    def action(self, name, case):
        result = self.request("/ws/action", {"action": name, "model": "com.axelor.apps.base.db.Company", "data": {"context": {"case_id": case}}})
        self.samples[-1].update(action=name, case=case)
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


def verified_build_status(evidence):
    if evidence is None:
        return "UNRUN"
    needed = {"lab_commit", "host_commit", "aos_commit", "upstream_diff_exit_codes",
              "baseline_pin_blob_sha256", "expected_baseline_pin_blob_sha256", "suites", "war_sha256"}
    if not needed.issubset(evidence):
        return "UNRUN"
    if evidence["host_commit"] != "1119727a3b53c8387b7fab535e184c25154d2eac" or evidence["aos_commit"] != "0c70d561b19fc454eba9fdd41689258846626d75":
        return "FAIL"
    if evidence["upstream_diff_exit_codes"] != {"host": 0, "aos": 0}:
        return "FAIL"
    if evidence["baseline_pin_blob_sha256"] != evidence["expected_baseline_pin_blob_sha256"]:
        return "FAIL"
    for name, count in {"CencomunModuleTest": 2, "MoneyPolicyTest": 7, "TestTaxNumberHelper": 16}.items():
        suite = evidence["suites"].get(name)
        if suite is None:
            return "UNRUN"
        if suite != {"tests": count, "failures": 0, "errors": 0, "skipped": 0}:
            return "FAIL"
    if len(evidence["lab_commit"]) != 40 or len(evidence["war_sha256"]) != 64:
        return "UNRUN"
    return "PASS"


def criteria_for(rows, build_evidence=None):
    # Reject missing/obsolete evidence even if a caller supplied a PASS label.
    rows = [{**r, "status": "UNRUN" if r.get("observed_revision", 0) < r["minimum_revision"]
             or (r["status"] == "PASS" and (not r.get("complete") or not r.get("evidence"))) else r["status"]} for r in rows]
    result = []
    for number in range(1, 15):
        attached = [r for r in rows if number in r["criteria"]]
        status = max((r["status"] for r in attached), key=RANK.get) if attached else "UNRUN"
        reason = "All attached groups must meet their minimum revision"
        if number == 2:
            status, reason = verified_build_status(build_evidence), "Requires actual build suites, WAR hash, pins and clean pinned upstream diffs from this run"
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
    assert len(invoice["payments"]) == 2 and all(p["status"] == 1 for p in invoice["payments"]), invoice["payments"]
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


def run_product_cases(admin, base, fixtures, output, row):
    """Native CRUD under the real operator; every warranty write is reread after commit."""
    start = time.perf_counter()
    evidence = {"case": "PROD01-04", "reference": REFERENCE, "revision": 1, "steps": []}
    operator = NativeClient(base)
    model = "com.cencomun.core.db.CcmProductProfile"
    fields = ["company", "product", "marketplaceEnabled", "casheaEnabled", "casheaPrice",
              "supplierReference", "warrantyQuantity", "warrantyUnit", "condition"]
    def fetch(identity):
        result = operator.request(f"/ws/rest/{model}/{identity}/fetch", {"fields": fields})
        assert result.get("status") == 0 and len(result["data"]) == 1, result
        return result["data"][0]
    def update(identity, **values):
        current = fetch(identity)
        result = operator.request(f"/ws/rest/{model}", {"data": {"id": identity, "version": current["version"], **values}})
        assert result.get("status") == 0, result
        # No returned in-memory object is accepted as persistence evidence.
        return fetch(identity)
    try:
        setup = admin.action("ccm-core-products-prepare", "PROD")
        evidence["setup"] = setup
        operator.login("ccm-operator", "CoreLab-operator-2026!")
        evidence["actor"] = "ccm-operator"
        identities = {p["product_code"]: p for p in setup["profiles"]}
        assert set(identities) == {"P001", "P002", "P003"}
        identity = identities["P001"]["id"]
        for quantity, unit in [(30, "DAY"), (6, "MONTH"), (1, "YEAR"), (0, "DAY"), (0, "MONTH"), (0, "YEAR")]:
            current = update(identity, warrantyQuantity=quantity, warrantyUnit=unit)
            assert (current["warrantyQuantity"], current["warrantyUnit"]) == (quantity, unit), current
            evidence["steps"].append({"case": "warranty", "requested": [quantity, unit], "persisted": current})
            print("::notice title=Native product warranty::" + json.dumps(evidence["steps"][-1]), flush=True)
        disabled = update(identity, casheaEnabled=False)
        assert disabled["casheaEnabled"] is False and Decimal(disabled["casheaPrice"]) == Decimal("50.00")
        evidence["steps"].append({"case": "disabled-price-retained", "persisted": disabled})
        print("::notice title=Native product disabled price::" + json.dumps(evidence["steps"][-1]), flush=True)
        update(identity, casheaEnabled=True, warrantyQuantity=12, warrantyUnit="MONTH")
        exported = {}
        for product in json.loads((fixtures / "products.json").read_bytes()):
            current = fetch(identities[product["id"]]["id"])
            assert current["company"]["id"] == setup["company_id"]
            assert current["product"]["id"] == identities[product["id"]]["product_id"]
            for key, native in [("marketplace_enabled", "marketplaceEnabled"), ("cashea_enabled", "casheaEnabled"),
                                ("supplier_reference", "supplierReference"), ("warranty_quantity", "warrantyQuantity"),
                                ("warranty_unit", "warrantyUnit"), ("condition", "condition")]:
                assert current[native] == product[key], (product["id"], key, current)
            assert Decimal(current["casheaPrice"]) == Decimal(product["price"])
            exported[product["id"]] = current
        evidence.update(status="PASS", complete=True, final_native_profiles=exported)
    except AssertionError as error:
        evidence.update(status="FAIL", complete=False, error=str(error)[:2500], error_type=type(error).__name__)
    except Exception as error:
        evidence.update(status=exception_status(error), complete=False, error=str(error)[:2500], error_type=type(error).__name__)
    evidence["seconds"] = round(time.perf_counter() - start, 3)
    evidence["http_samples"] = operator.samples
    (output / "PROD01-04.json").write_text(json.dumps(evidence, indent=2) + "\n")
    row.update(status=evidence["status"], observed_revision=1, complete=evidence["complete"],
               evidence="PROD01-04.json", reason=evidence.get("error", "Executed native operator CRUD with committed rereads"))
    print("::notice title=Core independent PROD01-04::" + json.dumps({k: v for k, v in evidence.items() if k not in ["steps", "http_samples"]})[:3800], flush=True)
    return evidence


def run_search_cases(base, fixtures, output, row):
    start = time.perf_counter()
    evidence = {"case": "SEARCH01-04-NATIVE", "reference": REFERENCE, "revision": 1, "steps": []}
    reader = NativeClient(base)
    specification = json.loads((fixtures / "scenarios.json").read_bytes())["search"]
    def native_search(model, criteria, fields):
        result = reader.request(f"/ws/rest/{model}/search", {"data": {"criteria": criteria}, "fields": fields, "limit": 100})
        assert result.get("status") == 0, result
        return result.get("data", [])
    try:
        reader.login("ccm-reader", "CoreLab-reader-2026!")
        evidence["actor"] = "ccm-reader"
        try:
            reader.request("/ws/ccm/products/search?company_id=OTHER-LAB&q=P001")
        except urllib.error.HTTPError as error:
            assert error.code == 403, error.code
            evidence["steps"].append({"case": "foreign-company-denied", "http_status": error.code})
        else:
            raise AssertionError("Foreign company search was accepted")
        for text, expected in specification["products"].items():
            response = reader.request("/ws/ccm/products/search?" + urllib.parse.urlencode({"company_id": "CCM-LAB-001", "q": text}))
            assert [r["id"] for r in response["items"]] == expected, response
            evidence["steps"].append({"case": "product-query", "query": text, "persisted": response})
        seen = []
        for page in (1, 2):
            response = reader.request("/ws/ccm/products/search?" + urllib.parse.urlencode({"company_id": "CCM-LAB-001", "q": "ficticio", "page": page, "page_size": 2}))
            assert response["total"] == 3, response
            seen.extend(r["id"] for r in response["items"])
            evidence["steps"].append({"case": "complete-pages", "persisted": response})
        assert seen == ["P001", "P002", "P003"]
        for field, text in [("name", specification["customer"]["name"]), ("mobilePhone", specification["customer"]["phone"])]:
            found = native_search("com.axelor.apps.base.db.Partner", [{"fieldName": field, "operator": "=", "value": text}], ["partnerSeq", "name", "mobilePhone"])
            assert [r["partnerSeq"] for r in found] == specification["customer"]["expected"], found
            evidence["steps"].append({"case": "native-customer-query", "field": field, "query": text, "persisted": found})
        found = native_search("com.axelor.apps.stock.db.TrackingNumber", [{"fieldName": "trackingNumberSeq", "operator": "=", "value": specification["serial"]["reference"]}], ["trackingNumberSeq", "product.code"])
        assert len(found) == 1 and found[0].get("product.code", found[0].get("product", {}).get("code")) == "P001", found
        evidence["steps"].append({"case": "native-serial-query", "persisted": found, "serial_inventory_tracking_tested": False})
        found = native_search("com.axelor.apps.account.db.Invoice", [{"fieldName": "externalReference", "operator": "=", "value": specification["invoice"]["reference"]}], ["externalReference", "saleOrder.externalReference"])
        if not found:
            evidence.update(status="BLOCKED", complete=False, error="CO00 native invoice prerequisite has not committed; independent product/customer/serial searches executed")
        else:
            assert len(found) == 1 and found[0].get("saleOrder.externalReference", found[0].get("saleOrder", {}).get("externalReference")) == "CCM-CO00", found
            evidence["steps"].append({"case": "native-invoice-query", "persisted": found})
            evidence.update(status="PASS", complete=True)
    except AssertionError as error:
        evidence.update(status="FAIL", complete=False, error=str(error)[:2500], error_type=type(error).__name__)
    except Exception as error:
        evidence.update(status=exception_status(error), complete=False, error=str(error)[:2500], error_type=type(error).__name__)
    evidence["seconds"] = round(time.perf_counter() - start, 3)
    evidence["http_samples"] = reader.samples
    (output / "SEARCH01-04-NATIVE.json").write_text(json.dumps(evidence, indent=2) + "\n")
    row.update(status=evidence["status"], observed_revision=1, complete=evidence["complete"], evidence="SEARCH01-04-NATIVE.json",
               reason=evidence.get("error", "Native queries and complete nonduplicated pages under the real reader"))
    for step in evidence["steps"]:
        print("::notice title=Native search step::" + json.dumps({"case": evidence["case"], "step": step}), flush=True)
    print("::notice title=Core independent SEARCH01-04::" + json.dumps({k: v for k, v in evidence.items() if k not in ["http_samples", "steps"]})[:3800], flush=True)
    return evidence


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
            prepared = client.action("ccm-core-native-prepare", case)
            (output / f"{case}-preparation.json").write_text(json.dumps(prepared, indent=2) + "\n")
            # A fresh request proves committed configuration before the native isolated increment.
            configuration = client.action("ccm-core-native-inspect", case)
            (output / f"{case}-prepared-export.json").write_text(json.dumps(configuration, indent=2) + "\n")
            assert prepared.get("status") == "PASS", ("Fixture preparation failed", prepared)
            assert len(configuration["company_ids"]) == 1
            assert len(configuration["sequences"]) == 12, configuration["sequences"]
            assert all(s["id"] and len(s["versions"]) == 1 and s["versions"][0]["id"] for s in configuration["sequences"])
            print(f"::notice title=Native {case} committed sequences::" + json.dumps({"case": case, "sequences": configuration["sequences"]}), flush=True)
            observed = client.action("ccm-core-native-gate", case)
            # Independent new HTTP request reads durable records, after any rollback.
            native = client.action("ccm-core-native-inspect", case)
            (output / f"{case}-native-export.json").write_text(json.dumps(native, indent=2) + "\n")
            for section in ["stock", "invoices", "moves", "deliveries", "sale_order_ids", "company_ids"]:
                value = json.dumps({"case": case, "section": section, "records": native[section]}, ensure_ascii=True)
                # Keep complete sections only; the full export is retained in the artifact.
                if len(value) <= 3700:
                    print(f"::notice title=Native {case} {section}::" + value.replace("%", "%25"), flush=True)
            observed["committed_native_export"] = f"{case}-native-export.json"
            if observed.get("status") == "PASS":
                oracle = json.loads((fixtures / "oracle.json").read_bytes())
                try:
                    observed["asserted_native_economics"] = assert_native_economics(native, oracle[case])
                except Exception as error:
                    observed.update(status="FAIL", error=str(error), error_type=type(error).__name__, failed_stage="native-oracle-assertions")
        except AssertionError as error:
            observed = {"case": case, "status": "FAIL", "error": str(error), "error_type": type(error).__name__}
        except Exception as error:
            observed = {"case": case, "status": "BLOCKED", "error": str(error)[:2500], "error_type": type(error).__name__}
        observed["seconds"] = round(time.perf_counter() - start, 3)
        observed["sequence"] = len(gates) + 1
        gates.append(observed)
        row = by_case[case + "-NATIVE"]
        # Administrator economics is a partial check. Role/state/atomicity subcases
        # still need their own executed evidence before the complete group can PASS.
        row.update(status="UNRUN" if observed["status"] == "PASS" else observed["status"], observed_revision=1,
                   complete=False, partial_gate_status=observed["status"],
                   reason=observed.get("failed_stage", "native economic gate") + ": " + observed.get("error", ""), evidence=f"{case}-gate.json")
        (output / f"{case}-gate.json").write_text(json.dumps(observed, indent=2) + "\n")
        # Persist and publish impediment before expanding independent checks.
        message = json.dumps(observed, ensure_ascii=True).replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
        print(f"::notice title=Core gate {case}::{message[:3800]}", flush=True)
    (output / "gate-impediments.json").write_text(json.dumps(gates, indent=2) + "\n")
    # Independent catalog fields run after the economic impediments have been persisted.
    products = run_product_cases(client, base, fixtures, output, by_case["PROD01-04"])
    search = run_search_cases(base, fixtures, output, by_case["SEARCH01-04-NATIVE"])
    results = {"reference": REFERENCE, "coverage_revision": 2,
               "groups": rows, "criteria": criteria_for(rows),
               "counts": dict(Counter(r["status"] for r in rows)),
               "patch_scenarios": {"status": "UNRUN", "count": 6},
               "scope": "Actual native gates. Policy unit tests do not mark native groups PASS."}
    (output / "coverage.json").write_text(json.dumps(results, indent=2) + "\n")
    (output / "metrics.json").write_text(json.dumps({"gates": [{"case": g["case"], "seconds": g["seconds"], "status": g["status"]} for g in gates],
                                                   "independent": [{"case": c["case"], "seconds": c["seconds"], "status": c["status"]} for c in [products, search]],
                                                   "http_samples": client.samples, "platform": platform.platform(),
                                                   "cpu_count": os.cpu_count(), "cpu_affinity": len(os.sched_getaffinity(0)),
                                                   "disk_free_bytes": shutil.disk_usage(output).free,
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
