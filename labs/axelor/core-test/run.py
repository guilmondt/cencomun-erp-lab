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
from decimal import Decimal, ROUND_HALF_UP
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
    for suite in evidence["suites"].values():
        if suite.get("tests", 0) <= 0 or any(suite.get(key, 0) != 0 for key in ("failures", "errors", "skipped")):
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


def assert_invoice_runtime(configuration):
    assert configuration.get("native_app_invoice_id", 0) > 0, "Missing native AppInvoice identity"
    for field in ("autoGenerateInvoicePrintingFileOnSaleInvoice", "isVentilationSkipped",
                  "persisted_autoGenerateInvoicePrintingFileOnSaleInvoice", "persisted_isVentilationSkipped"):
        assert configuration.get(field) is False, "Core LAB invoice runtime flag must be false: " + field


def assert_native_configuration(configuration):
    assert_invoice_runtime(configuration["invoice_runtime_configuration"])
    assert configuration["company_id"] > 0 and configuration["legal_partner_id"] > 0
    assert configuration["legal_vat_system"] == 2, "Native legal partner delivery/accrual regime required"
    customers = {p["code"]: p for p in configuration["customers"]}
    assert set(customers) == {"C001", "C002", "CBANK"}
    assert all(p["invoicing_address_id"] > 0 for p in customers.values()), "Native invoicing address missing"
    accounts = {a["code"]: a for a in configuration["accounts"]}
    for code in ["CCM-AR", "CCM-REVENUE", "CCM-TAX"]:
        assert accounts[code]["id"] > 0 and accounts[code]["vat_system"] == 1, "Native accrual account regime required: " + code


def assert_native_invoice_linkage(link, invoice_id, company_id, order_id, order_reference):
    assert link["source"] == "InvoiceLine.saleOrderLine.saleOrder", "Native source FK chain required"
    assert link["native_invoice_id"] == invoice_id > 0
    assert link["native_company_id"] == company_id > 0, "Foreign company invoice linkage"
    assert link["header_sale_order_id"] == order_id > 0, "Native INVOICE_ALL header order required"
    assert link["header_sale_order_company_id"] == company_id, "Foreign company header order"
    assert link["header_sale_order_reference"] == order_reference, "Wrong native header reference"
    lines = link["line_links"]
    assert len(lines) == 2, "Two actual source-linked native invoice product lines required"
    assert {l["product_code"] for l in lines} == {"P001", "P002"}
    assert len({l["invoice_line_id"] for l in lines}) == len({l["sale_order_line_id"] for l in lines}) == 2
    for line in lines:
        assert line["invoice_line_id"] > 0 and line["sale_order_line_id"] > 0
        assert line["parent_invoice_id"] == invoice_id, "Native source line belongs to another invoice"
        assert line["sale_order_id"] == order_id > 0 and line["sale_order_reference"] == order_reference
        assert line["sale_order_company_id"] == company_id, "Foreign company source order"


def assert_native_economics(native, expected):
    quantities = {x["code"]: Decimal(x["current_qty"]) for x in native["stock"]}
    assert [quantities[f"P{i:03}"] for i in (1, 2, 3)] == list(map(Decimal, expected["stock"])), quantities
    value = sum(Decimal(x["current_qty"]) * Decimal(x["avg_price"]) for x in native["stock"])
    assert value == Decimal(expected["stock_value"]), ("native stock valuation", value)
    assert len(native["sale_order_ids"]) == len(native["deliveries"]) == len(native["invoices"]) == 1, "One committed native sale/delivery/invoice required"
    assert native["deliveries"][0]["status"] == 3, native["deliveries"]
    invoice = native["invoices"][0]
    assert_native_invoice_linkage(invoice["native_source_linkage"], invoice["id"], native["company_ids"][0],
                                  native["sale_order_ids"][0], "CCM-" + native["case"])
    assert int(invoice["statusSelect"]) == 3, invoice
    for key, field in [("revenue", "exTaxTotal"), ("tax", "taxTotal"), ("gross", "inTaxTotal"), ("customer_balance_final", "amountRemaining")]:
        assert Decimal(invoice[field]) == Decimal(expected[key]), (field, invoice[field], expected[key])
    invoice_lines = invoice.get("lines", [])
    assert len(invoice_lines) == 2, ("native invoice product lines", invoice_lines)
    assert {l["id"] for l in invoice_lines} == {l["invoice_line_id"] for l in invoice["native_source_linkage"]["line_links"]}, "Invoice product lines differ from native source-linked lines"
    taxable = Decimal(expected["tax"]) != 0
    expected_lines = {"P001": (Decimal(2), Decimal("100.00"), Decimal("110.00" if taxable else "100.00")),
                      "P002": (Decimal(1), Decimal("25.00"), Decimal("27.50" if taxable else "25.00"))}
    assert {line["code"] for line in invoice_lines} == set(expected_lines)
    for line in invoice_lines:
        actual = tuple(Decimal(line[field]) for field in ["qty", "ex_tax_total", "in_tax_total"])
        assert actual == expected_lines[line["code"]], ("native invoice product line", line)
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


def assert_native_bank_book(native, fixtures):
    """Require four actual advance payments and their native balanced posted moves."""
    expected = {r["reference"]: r for r in fixtures}
    vouchers = native["vouchers"]
    assert len(vouchers) == len(expected) == 4, vouchers
    assert {r["reference"] for r in vouchers} == set(expected)
    assert len({r["id"] for r in vouchers}) == 4
    moves, lines = set(), set()
    for voucher in vouchers:
        want = expected[voucher["reference"]]
        amount = Decimal(want["amount"])
        assert voucher["status"] == 2 and voucher["allocation_ids"] == [], voucher
        assert voucher["company_id"] == native["company_id"] and voucher["company_code"] == "CCM-LAB-001"
        assert voucher["customer_id"] == want["customer_id"] and voucher["partner_id"]
        assert voucher["currency"] == want["currency"] and voucher["payment_date"] == want["date"]
        assert Decimal(voucher["paid_amount"]) == Decimal(voucher["remaining_amount"]) == amount
        move = voucher["move"]
        assert move["status"] == 3 and move["voucher_id"] == voucher["id"]
        assert move["company_id"] == voucher["company_id"] and move["date"] == want["date"]
        assert move["id"] not in moves
        moves.add(move["id"])
        assert len(move["lines"]) == 2
        amounts = {}
        for line in move["lines"]:
            assert line["id"] not in lines
            lines.add(line["id"])
            assert line["account"] not in amounts
            amounts[line["account"]] = (Decimal(line["debit"]), Decimal(line["credit"]))
            if line["account"] == "CCM-AR":
                # AOS stores pending credits as -(credit - amountPaid). The
                # voucher's unallocated business amount above remains positive.
                assert Decimal(line["remaining"]) == -amount, line
        assert amounts == {"CCM-BANK": (amount, Decimal(0)), "CCM-AR": (Decimal(0), amount)}, amounts
    return {"native_voucher_ids": sorted(v["id"] for v in vouchers), "native_move_ids": sorted(moves),
            "native_move_line_ids": sorted(lines), "unallocated_total": str(sum(Decimal(v["remaining_amount"]) for v in vouchers))}


def run_bank_book_cases(admin, fixtures, output, row):
    start = time.perf_counter()
    evidence = {"case": "BANK-BOOK-FIXTURE", "reference": REFERENCE, "revision": 1, "actor": "admin", "steps": []}
    expected = json.loads((fixtures / "bank-book.json").read_bytes())
    try:
        evidence["setup"] = admin.action("ccm-core-bank-book-prepare", "BANKBOOK")
        admin.action("ccm-core-bank-book-post", "BANKBOOK")
        native = admin.action("ccm-core-bank-book-inspect", "BANKBOOK")
        evidence["native_export"] = native
        for voucher in native["vouchers"]:
            print("::notice title=Native bank book inspected receipt::" + json.dumps({"case": evidence["case"], "inspected_receipt": voucher}), flush=True)
        evidence["native_assertions"] = assert_native_bank_book(native, expected)
        for voucher in native["vouchers"]:
            step = {"case": "native-advance-receipt", "persisted": voucher}
            evidence["steps"].append(step)
            print("::notice title=Native bank book receipt::" + json.dumps({"case": evidence["case"], "step": step}), flush=True)
        admin.action("ccm-core-bank-book-post", "BANKBOOK")
        replay = admin.action("ccm-core-bank-book-inspect", "BANKBOOK")
        assert_native_bank_book(replay, expected)
        assert replay == native, "Fixture replay changed persisted native vouchers or moves"
        step = {"case": "fixture-replay", "persisted_ids": evidence["native_assertions"], "native_export_identical": True}
        evidence["steps"].append(step)
        print("::notice title=Native bank book replay::" + json.dumps({"case": evidence["case"], "step": step}), flush=True)
        evidence.update(status="PASS", complete=True)
    except AssertionError as error:
        evidence.update(status="FAIL", complete=False, error=str(error)[:2500], error_type=type(error).__name__)
    except Exception as error:
        evidence.update(status=exception_status(error), complete=False, error=str(error)[:2500], error_type=type(error).__name__)
    evidence["seconds"] = round(time.perf_counter() - start, 3)
    (output / "BANK-BOOK-FIXTURE.json").write_text(json.dumps(evidence, indent=2) + "\n")
    row.update(status=evidence["status"], observed_revision=1, complete=evidence["complete"], evidence="BANK-BOOK-FIXTURE.json",
               reason=evidence.get("error", "Four confirmed native advance payments with posted GL and unallocated balances"))
    print("::notice title=Core independent BANK-BOOK-FIXTURE::" + json.dumps({k: v for k, v in evidence.items() if k != "steps"}), flush=True)
    return evidence


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
        persisted_setup = admin.action("ccm-core-products-inspect", "PROD")
        evidence["persisted_setup"] = persisted_setup
        assert len(persisted_setup["profiles"]) == 3 and len(persisted_setup["users"]) == 2
        assert all(u["active"] and not u["blocked"] and u["native_role_present"] and u["credentials_match"]
                   and u["company_id"] == setup["company_id"] for u in persisted_setup["users"]), persisted_setup
        assert sorted(persisted_setup["profiles"], key=lambda p: p["id"]) == sorted(
            [{**p, "company_id": setup["company_id"]} for p in setup["profiles"]], key=lambda p: p["id"])
        print("::notice title=Native committed product actors::" + json.dumps({"case": "PROD01-04", "persisted_setup": persisted_setup}), flush=True)
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
    print("::notice title=Core independent PROD01-04::" + json.dumps({k: v for k, v in evidence.items() if k not in ["steps", "http_samples"]}), flush=True)
    return evidence


def assert_native_fx_conversions(observed, fixture, persisted):
    rates = {r["id"]: r for r in persisted["rates"]}
    assert len(observed) == len(fixture["payments"])
    for actual, expected in zip(observed, fixture["payments"]):
        assert actual["id"] == expected["id"] and actual["date"] == expected["date"]
        assert actual["native_conversion_id"] in rates, "Conversion has no durable native rate"
        native = rates[actual["native_conversion_id"]]
        assert native["source"] == "USD" and native["target"] == "VES"
        assert native["from_date"] == native["to_date"] == actual["date"]
        assert Decimal(actual["rate"]) == Decimal(native["rate"])
        assert Decimal(actual["total"]) == Decimal(expected["expected_total"])
        assert sum(map(Decimal, actual["lines"])) == Decimal(actual["total"])
        if "expected_lines" in expected:
            assert actual["lines"] == expected["expected_lines"], "Must round each native line before summing"
    assert len(persisted["authorizations"]) == 1
    authorization = persisted["authorizations"][0]
    assert authorization["id"] > 0 and authorization["approved_by"] == "ccm-manager"
    assert authorization["external_id"] == "FX-AUTH" and authorization["company_id"] > 0
    assert authorization["reason"] == fixture["manual_rate"]["reason"]
    assert rates[authorization["native_conversion_id"]]["from_date"] == fixture["manual_rate"]["date"]
    assert Decimal(rates[authorization["native_conversion_id"]]["rate"]) == Decimal(fixture["manual_rate"]["rate"])


def assert_native_fx(observed, fixture, persisted):
    """A conversion is partial; acceptance also needs four committed native receipts."""
    assert_native_fx_conversions(observed, fixture, persisted)
    assert_invoice_runtime(persisted.get("invoice_runtime_configuration", {}))
    assert persisted.get("read_boundary") == "separate-http-after-payment-commit", "Missing post-commit native payment reads"
    assert persisted["company_id"] > 0 and persisted["company_code"] == "CCM-LAB-001"
    invoices, payments = persisted.get("invoices", []), persisted.get("payments", [])
    assert len(invoices) == 3 and len(payments) == 4, "FX parity requires three USD invoices and four native payments"
    assert len({p["id"] for p in payments}) == 4 and all(p["id"] > 0 for p in payments)
    invoice_ids, move_ids, line_ids, reconcile_ids = set(), set(), set(), set()
    def posted(move, currency, day):
        assert move["id"] > 0 and move["id"] not in move_ids
        move_ids.add(move["id"])
        assert move["status"] == 3 and move["company_id"] == persisted["company_id"]
        assert move["currency"] == currency and move["company_currency"] == "USD" and move["date"] == day
        assert len(move["lines"]) == 2
        for line in move["lines"]:
            assert line["id"] > 0 and line["id"] not in line_ids
            line_ids.add(line["id"])
        assert sum(Decimal(l["debit"]) for l in move["lines"]) == sum(Decimal(l["credit"]) for l in move["lines"])
        return {l["account"]: l for l in move["lines"]}
    for actual, expected in zip(observed, fixture["payments"]):
        reference = "FX-" + expected["id"]
        matching = [i for i in invoices if i["reference"] == reference]
        assert len(matching) == 1
        invoice = matching[0]
        assert invoice["id"] > 0 and invoice["id"] not in invoice_ids
        invoice_ids.add(invoice["id"])
        usd_total = sum(map(Decimal, expected["lines"]))
        assert invoice["company_id"] == persisted["company_id"] and invoice["customer"] == "C002"
        assert invoice["date"] == expected["date"] and invoice["currency"] == "USD" and invoice["status"] == 3
        assert Decimal(invoice["total"]) == Decimal(invoice["paid"]) == usd_total and Decimal(invoice["remaining"]) == 0
        invoice_lines = posted(invoice["move"], "USD", expected["date"])
        assert set(invoice_lines) == {"CCM-AR", "CCM-REVENUE"}
        assert Decimal(invoice_lines["CCM-AR"]["debit"]) == Decimal(invoice_lines["CCM-REVENUE"]["credit"]) == usd_total
        assert Decimal(invoice_lines["CCM-AR"]["credit"]) == Decimal(invoice_lines["CCM-REVENUE"]["debit"]) == 0
        assert Decimal(invoice_lines["CCM-AR"]["amountRemaining"]) == 0
        native = [p for p in payments if p["invoice_id"] == invoice["id"]]
        assert len(native) == len(expected["lines"])
        assert sorted(actual["native_payment_ids"]) == sorted(p["id"] for p in native)
        assert actual["native_invoice_id"] == invoice["id"]
        for index, (source, converted) in enumerate(zip(expected["lines"], actual["lines"]), 1):
            matching = [p for p in native if p["reference"] == reference + "-" + str(index)]
            assert len(matching) == 1
            payment = matching[0]
            assert payment["status"] == 1 and payment["currency"] == "VES" and payment["date"] == expected["date"]
            assert Decimal(payment["amount"]) == Decimal(converted)
            assert payment["observed_payment_day_conversion_id"] == actual["native_conversion_id"]
            assert Decimal(payment["observed_payment_day_rate"]) == Decimal(actual["rate"])
            lines = posted(payment["move"], "VES", expected["date"])
            assert set(lines) == {"CCM-CASH-VES", "CCM-AR"}
            cash, receivable = lines["CCM-CASH-VES"], lines["CCM-AR"]
            assert Decimal(cash["debit"]) == Decimal(receivable["credit"]) == Decimal(source)
            assert Decimal(cash["credit"]) == Decimal(receivable["debit"]) == 0
            assert Decimal(cash["currencyAmount"]) == Decimal(converted)
            assert Decimal(receivable["currencyAmount"]) == -Decimal(converted)
            effective = (Decimal(source) / Decimal(converted)).quantize(Decimal(".000001"), rounding=ROUND_HALF_UP)
            assert Decimal(cash["currencyRate"]) == Decimal(receivable["currencyRate"]) == effective
            assert Decimal(receivable["amountRemaining"]) == 0
            reconcile = payment["reconcile"]
            assert reconcile["id"] > 0 and reconcile["id"] not in reconcile_ids and reconcile["status"] == 2
            reconcile_ids.add(reconcile["id"])
            assert Decimal(reconcile["amount"]) == Decimal(source)
            assert reconcile["debit_line_id"] == invoice_lines["CCM-AR"]["id"]
            assert reconcile["credit_line_id"] == receivable["id"]


def fx_notice_summary(evidence):
    """Keep a complete coverage notice within Actions' boundary; retain full JSON separately."""
    fields = ("case", "reference", "revision", "status", "complete", "seconds", "operator", "manager",
              "partial_conversion_status", "error", "error_type", "native_http_error", "inspection_error")
    summary = {key: evidence[key] for key in fields if key in evidence}
    summary["full_evidence_file"] = evidence["case"] + ".json"
    error_fields = [key for key in ("error", "native_http_error", "inspection_error") if key in summary]
    while len(json.dumps(summary)) > 3200:
        largest = max(error_fields, key=lambda key: len(json.dumps(summary[key])))
        value = str(summary[largest])
        summary[largest] = value[:len(value) // 2] + " [complete details in full_evidence_file]"
    return summary


def run_fx_payment_cases(operator, admin, inputs, body, evidence):
    """Each native invoice/receipt transaction is independent; a failure cannot skip later dates."""
    results, failures = [], []
    evidence["payment_attempts"] = []
    for item in inputs:
        attempt = {"case": item["id"]}
        before, result = None, None
        try:
            before = admin.action("ccm-core-fx-inspect", "FX")
            result = operator.request("/ws/ccm/lab/currency/payment", body(item))
            attempt["result"] = result
        except Exception as error:
            attempt.update(error=str(error)[:500], error_type=type(error).__name__)
            if isinstance(error, urllib.error.HTTPError):
                attempt.update(http_status=error.code, native_http_error=error.read().decode(errors="replace")[:3500])
        try:
            # This separate request follows the commit or rollback of the native payment request.
            committed = admin.action("ccm-core-fx-inspect", "FX")
            attempt["persisted"] = committed
            if result is not None:
                evidence["steps"].append({"case": "committed-payment-case", "result": result,
                    "persisted": {"company_id": committed["company_id"], "company_code": committed["company_code"],
                        "read_boundary": "separate-http-after-payment-commit",
                        "invoices": [i for i in committed["invoices"] if i["id"] == result["native_invoice_id"]],
                        "payments": [p for p in committed["payments"] if p["id"] in result["native_payment_ids"]]}})
                results.append(result)
            elif before is not None:
                attempt["native_effects_unchanged"] = before == committed
        except Exception as error:
            attempt["inspection_error"] = str(error)[:500]
        evidence["payment_attempts"].append(attempt)
        if "error" in attempt or "inspection_error" in attempt:
            failures.append(attempt)
    if failures:
        evidence["payment_failures"] = failures
        first_native = next((f["native_http_error"] for f in failures if "native_http_error" in f), None)
        if first_native is not None:
            evidence["native_http_error"] = first_native
        raise RuntimeError("Native payment cases failed: " + "; ".join(
            f["case"] + ": " + f.get("error", f.get("inspection_error", "")) for f in failures))
    return results


def run_fx_cases(admin, base, fixtures, output, row):
    start = time.perf_counter()
    evidence = {"case": "FX01-03-MONEY01-03", "reference": REFERENCE, "revision": 1, "steps": []}
    operator, manager = NativeClient(base), NativeClient(base)
    specification = json.loads((fixtures / "fx.json").read_bytes())
    profile = json.loads((fixtures / "profile.json").read_bytes())
    def body(item):
        # Expected fixture values remain client assertions, never service input.
        return {**{k: v for k, v in item.items() if k in ("id", "date", "lines", "rate", "reason")},
            "company_id": profile["company_id"]}
    def rejected(client, path, payload, status):
        try:
            client.request(path, payload)
        except urllib.error.HTTPError as error:
            assert error.code == status, (error.code, error.read().decode()[:2000])
            return {"http_status": error.code}
        raise AssertionError("Required FX rejection was accepted")
    try:
        evidence["preparation"] = admin.action("ccm-core-fx-prepare", "FX")
        before = admin.action("ccm-core-fx-inspect", "FX")
        assert len(before["rates"]) == 2 and before["authorizations"] == [], before
        assert {r["from_date"]: Decimal(r["rate"]) for r in before["rates"]} == {d: Decimal(v) for d,v in profile["rates"].items()}
        operator.login("ccm-operator", "CoreLab-operator-2026!")
        evidence["operator"] = "ccm-operator"
        observations = []
        for input in specification["payments"][:2]:
            actual = operator.request("/ws/ccm/lab/currency/convert", body(input))
            observations.append(actual); evidence["steps"].append({"case": input["id"], "native_conversion": actual})
        denied = rejected(operator, "/ws/ccm/lab/currency/payment", body({"id": "FX-MISSING", "date": "2026-10-03", "lines": ["1.00"]}), 422)
        assert admin.action("ccm-core-fx-inspect", "FX") == before, "Missing-rate rejection changed persisted rates"
        evidence["steps"].append({"case": "missing-rate", **denied, "native_effects_unchanged": True})
        authorization = body({"id": "FX-AUTH", **specification["manual_rate"]})
        denied = rejected(operator, "/ws/ccm/lab/currency/authorize", authorization, 403)
        assert admin.action("ccm-core-fx-inspect", "FX") == before, "Unauthorized operator changed a native rate"
        evidence["steps"].append({"case": "operator-denied", **denied, "native_effects_unchanged": True})
        manager.login("ccm-manager", "CoreLab-manager-2026!")
        evidence["manager"] = "ccm-manager"
        result = manager.request("/ws/ccm/lab/currency/authorize", authorization)
        persisted = admin.action("ccm-core-fx-inspect", "FX")
        assert result["native_conversion_id"] in [r["id"] for r in persisted["rates"]]
        evidence["steps"].append({"case": "manager-authorized", "result": result, "persisted": persisted})
        rounded = operator.request("/ws/ccm/lab/currency/convert", body(specification["payments"][2]))
        observations.append(rounded); evidence["steps"].append({"case": "MONEY-ROUND", "native_conversion": rounded})
        assert_native_fx_conversions(observations, specification, persisted)
        evidence.update(partial_conversion_status="PASS", conversion_observations=observations, persisted=persisted)
        payments = run_fx_payment_cases(operator, admin, specification["payments"], body, evidence)
        persisted = admin.action("ccm-core-fx-inspect", "FX")
        persisted["read_boundary"] = "separate-http-after-payment-commit"
        observations = payments
        assert_native_fx(observations, specification, persisted)
        evidence.update(status="PASS", complete=True, observations=observations, persisted=persisted)
    except Exception as error:
        evidence.update(status=exception_status(error), complete=False, error=str(error)[:2500], error_type=type(error).__name__)
        if isinstance(error, urllib.error.HTTPError):
            evidence["native_http_error"] = error.read().decode(errors="replace")[:3500]
        try:
            # Retain any earlier committed payments even if a later case rolls back.
            evidence["persisted"] = admin.action("ccm-core-fx-inspect", "FX")
            evidence["persisted"]["read_boundary"] = "separate-http-after-payment-commit"
        except Exception as inspection_error:
            evidence["inspection_error"] = str(inspection_error)[:1500]
    evidence["seconds"] = round(time.perf_counter() - start, 3)
    evidence["http_samples"] = {"operator": operator.samples, "manager": manager.samples}
    (output / (evidence["case"] + ".json")).write_text(json.dumps(evidence, indent=2) + "\n")
    row.update(status=evidence["status"], observed_revision=1, complete=evidence["complete"], evidence=evidence["case"] + ".json",
        partial_conversion_status=evidence.get("partial_conversion_status", "UNRUN"),
        reason=evidence.get("error", "Four native VES payments, posted USD effects and invoice liquidation read after commit; native rates and actual manager authorization"))
    for step in evidence["steps"]:
        print("::notice title=Native FX step::" + json.dumps({"case": evidence["case"], "step": step}), flush=True)
    for failure in evidence.get("payment_failures", []):
        summary = fx_notice_summary({"case": evidence["case"], "reference": REFERENCE, "revision": 1,
            "status": "FAIL", "complete": False, **{k:v for k,v in failure.items() if k in
                ("error", "error_type", "native_http_error", "inspection_error")}})
        print("::notice title=Native FX failed payment case::" + json.dumps({"case": evidence["case"],
            "payment_case": failure["case"], "failure": summary,
            "native_effects_unchanged": failure.get("native_effects_unchanged")}), flush=True)
    print("::notice title=Core independent FX/MONEY::" + json.dumps(fx_notice_summary(evidence)), flush=True)
    return evidence


def review_native_fx(row, evidence, fixture):
    """Revalidate result files; never trust a preassigned complete/PASS claim."""
    persisted = evidence.get("persisted", {})
    conversions = evidence.get("conversion_observations", evidence.get("observations", []))
    try:
        assert_native_fx_conversions(conversions, fixture, persisted)
        row["partial_conversion_status"] = "PASS"
    except (AssertionError, KeyError, TypeError):
        pass
    if row.get("status") == "PASS" or row.get("complete"):
        try:
            assert_native_fx(evidence.get("observations", []), fixture, persisted)
        except (AssertionError, KeyError, TypeError) as error:
            missing_payments = len(persisted.get("payments", [])) != 4 or persisted.get("read_boundary") != "separate-http-after-payment-commit"
            row.update(status="UNRUN" if missing_payments else "FAIL", complete=False,
                reason="FX complete claim rejected: four native committed payments and posted settlement required; " + str(error))
    return row


def run_search_cases(admin, base, fixtures, output, row):
    start = time.perf_counter()
    evidence = {"case": "SEARCH01-04-NATIVE", "reference": REFERENCE, "revision": 1, "steps": []}
    reader = NativeClient(base)
    specification = json.loads((fixtures / "scenarios.json").read_bytes())["search"]
    def native_search(model, criteria, fields):
        result = reader.request(f"/ws/rest/{model}/search", {"data": {"criteria": criteria}, "fields": fields, "limit": 100})
        observation = {"case": "native-rest-inspection", "model": model, "criteria": criteria, "response": result}
        if model == "com.axelor.apps.base.db.Partner" and not result.get("data"):
            payload = {"data": {"criteria": criteria}, "fields": fields, "limit": 100}
            observation["administrator_comparison"] = admin.request(f"/ws/rest/{model}/search", payload)
            try:
                observation["reader_filter_diagnostics"] = reader.request("/ws/ccm/lab/search/diagnostics?" + urllib.parse.urlencode({
                    "company_id": "CCM-LAB-001", "name": specification["customer"]["name"]}))
            except Exception as error:
                observation["reader_filter_diagnostics_error"] = str(error)[:500]
                if isinstance(error, urllib.error.HTTPError):
                    observation["reader_filter_diagnostics_http_error"] = error.read().decode(errors="replace")[:1500]
        evidence.setdefault("native_queries", []).append(observation)
        print("::notice title=Native search inspection::" + json.dumps({"case": evidence["case"], "inspection": observation}), flush=True)
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
        try:
            reader.request("/ws/ccm/lab/invoice-links?" + urllib.parse.urlencode({
                "company_id": "OTHER-LAB", "reference": specification["invoice"]["reference"]}))
        except urllib.error.HTTPError as error:
            assert error.code == 403, error.code
            evidence["steps"][-1]["invoice_links_http_status"] = error.code
        else:
            raise AssertionError("Foreign company invoice linkage was accepted")
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
        failures, invoice_blocked = [], False
        def failed(case, error):
            failure = {"case": case, "status": exception_status(error), "error": str(error)[:500], "error_type": type(error).__name__}
            if isinstance(error, urllib.error.HTTPError):
                failure.update(http_status=error.code, native_http_error=error.read().decode(errors="replace")[:1500])
            failures.append(failure)
        for field, text in [("name", specification["customer"]["name"]), ("mobilePhone", specification["customer"]["phone"])]:
            try:
                found = native_search("com.axelor.apps.base.db.Partner", [{"fieldName": field, "operator": "=", "value": text}], ["partnerSeq", "name", "mobilePhone"])
                assert [r["partnerSeq"] for r in found] == specification["customer"]["expected"], found
                evidence["steps"].append({"case": "native-customer-query", "field": field, "query": text, "persisted": found})
            except Exception as error:
                failed("native-customer-query:" + field, error)
        try:
            found = native_search("com.axelor.apps.stock.db.TrackingNumber", [{"fieldName": "trackingNumberSeq", "operator": "=", "value": specification["serial"]["reference"]}], ["trackingNumberSeq", "product.code"])
            assert len(found) == 1 and found[0].get("product.code", found[0].get("product", {}).get("code")) == "P001", found
            evidence["steps"].append({"case": "native-serial-query", "persisted": found, "serial_inventory_tracking_tested": False})
        except Exception as error:
            failed("native-serial-query", error)
        try:
            found = native_search("com.axelor.apps.account.db.Invoice", [{"fieldName": "externalReference", "operator": "=", "value": specification["invoice"]["reference"]}], ["externalReference", "saleOrder.externalReference"])
            if not found:
                invoice_blocked = True
            else:
                assert len(found) == 1 and found[0]["externalReference"] == specification["invoice"]["reference"], found
                links = reader.request("/ws/ccm/lab/invoice-links?" + urllib.parse.urlencode({
                    "company_id": "CCM-LAB-001", "reference": specification["invoice"]["reference"]}))
                assert links["actor"] == "ccm-reader" and len(links["invoices"]) == 1, links
                linkage = links["invoices"][0]
                order_ids = {l["sale_order_id"] for l in linkage["line_links"]}
                assert len(order_ids) == 1, linkage
                assert_native_invoice_linkage(linkage, found[0]["id"], links["reader_company_id"], order_ids.pop(), "CCM-CO00")
                evidence["steps"].append({"case": "native-invoice-query", "persisted": found, "native_links": links})
        except Exception as error:
            failed("native-invoice-query", error)
        evidence["subcase_failures"] = failures
        if failures:
            status = max((f["status"] for f in failures), key=RANK.get)
            evidence.update(status=status, complete=False, error="Independent native search failures: " + ", ".join(f["case"] for f in failures))
        elif invoice_blocked:
            evidence.update(status="BLOCKED", complete=False, error="CO00 native invoice prerequisite has not committed; independent product/customer/serial searches executed")
        else:
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
    for failure in evidence.get("subcase_failures", []):
        print("::notice title=Native search failed subcase::" + json.dumps({"case": evidence["case"], "failure": failure}), flush=True)
    print("::notice title=Core independent SEARCH01-04::" + json.dumps({k: v for k, v in evidence.items() if k not in ["http_samples", "steps", "native_queries", "subcase_failures"]}), flush=True)
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
        prepared = None
        phase = "fixture-preparation"
        try:
            prepared = client.action("ccm-core-native-prepare", case)
            (output / f"{case}-preparation.json").write_text(json.dumps(prepared, indent=2) + "\n")
            # A fresh request proves committed configuration before the native isolated increment.
            configuration = client.action("ccm-core-native-inspect", case)
            (output / f"{case}-prepared-export.json").write_text(json.dumps(configuration, indent=2) + "\n")
            phase = "fixture-preparation-assertions"
            assert prepared.get("status") == "PASS", ("Fixture preparation failed", prepared)
            assert len(configuration["company_ids"]) == 1
            assert len(configuration["sequences"]) == 12, configuration["sequences"]
            assert all(s["id"] and len(s["versions"]) == 1 and s["versions"][0]["id"] for s in configuration["sequences"])
            assert_native_configuration(configuration["fixture_configuration"])
            print(f"::notice title=Native {case} committed fixture configuration::" + json.dumps({"case": case,
                "section": "fixture_configuration", "records": configuration["fixture_configuration"]}), flush=True)
            print(f"::notice title=Native {case} committed sequences::" + json.dumps({"case": case, "sequences": configuration["sequences"]}), flush=True)
            phase = "native-economic-gate"
            observed = client.action("ccm-core-native-gate", case)
            # Independent new HTTP request reads durable records, after any rollback.
            native = client.action("ccm-core-native-inspect", case)
            (output / f"{case}-native-export.json").write_text(json.dumps(native, indent=2) + "\n")
            for section in ["stock", "invoices", "moves", "fixture_opening_moves", "deliveries", "sale_order_ids", "company_ids"]:
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
            if prepared is not None and prepared.get("status") != "PASS":
                # Preserve the native failure and stack instead of burying both in
                # a Python tuple string without reference/stage metadata.
                observed = {**prepared, "status": "FAIL", "assertion_error": "Fixture preparation failed"}
            else:
                observed = {"case": case, "status": "FAIL", "error": str(error)[:2500], "error_type": type(error).__name__}
        except Exception as error:
            observed = {"case": case, "status": exception_status(error), "error": str(error)[:2500], "error_type": type(error).__name__}
        observed.setdefault("reference", REFERENCE)
        observed.setdefault("actor", "admin")
        if observed["status"] != "PASS":
            observed.setdefault("failed_stage", phase)
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
        print(f"::notice title=Core gate {case}::{message}", flush=True)
    (output / "gate-impediments.json").write_text(json.dumps(gates, indent=2) + "\n")
    # Independent catalog fields run after the economic impediments have been persisted.
    products = run_product_cases(client, base, fixtures, output, by_case["PROD01-04"])
    search = run_search_cases(client, base, fixtures, output, by_case["SEARCH01-04-NATIVE"])
    book = run_bank_book_cases(client, fixtures, output, by_case["BANK-BOOK-FIXTURE"])
    fx = run_fx_cases(client, base, fixtures, output, by_case["FX01-03-MONEY01-03"])
    results = {"reference": REFERENCE, "coverage_revision": 2,
               "groups": rows, "criteria": criteria_for(rows),
               "counts": dict(Counter(r["status"] for r in rows)),
               "patch_scenarios": {"status": "UNRUN", "count": 6},
               "scope": "Actual native gates. Policy unit tests do not mark native groups PASS."}
    (output / "coverage.json").write_text(json.dumps(results, indent=2) + "\n")
    metrics = {"metric_kind": "runtime", "reference": REFERENCE,
                                                   "gates": [{"case": g["case"], "seconds": g["seconds"], "status": g["status"]} for g in gates],
                                                   "independent": [{"case": c["case"], "seconds": c["seconds"], "status": c["status"]} for c in [products, search, book, fx]],
                                                   "http_samples": client.samples, "platform": platform.platform(),
                                                   "cpu_count": os.cpu_count(), "cpu_affinity": len(os.sched_getaffinity(0)),
                                                   "disk_free_bytes": shutil.disk_usage(output).free,
                                                   "http_call_counts": {"administrator": len(client.samples),
                                                       "product_operator": len(products["http_samples"]), "search_reader": len(search["http_samples"]),
                                                       "fx_operator": len(fx["http_samples"]["operator"]), "fx_manager": len(fx["http_samples"]["manager"])},
                                                   "native_action_counts": dict(Counter(s["action"] for s in client.samples if "action" in s)),
                                                   "benchmark": "UNRUN", "note": "Gate timings are not the required 1000-sample benchmark"}
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print("::notice title=Core measured runtime::" + json.dumps({k: v for k, v in metrics.items() if k != "http_samples"}), flush=True)
    print("::notice title=Core coverage::" + json.dumps({"reference": REFERENCE, "groups": results["counts"], "criteria": dict(Counter(r["status"] for r in results["criteria"]))}), flush=True)
    return 0 if all(r["status"] == "PASS" for r in rows) else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.base, args.fixtures, args.output))
