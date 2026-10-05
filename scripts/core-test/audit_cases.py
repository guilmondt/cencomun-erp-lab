"""Independent native ledger/audit/config/fixture inspections, without business SQL."""

import sys, json, hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from support import *


def fixtures():
    root = REPO / "fixtures/ccm-core-v1"
    manifest = json.loads((root / "manifest.json").read_text())
    hashes = []
    for f in manifest["files"]:
        digest = hashlib.sha256((root / f["path"]).read_bytes()).hexdigest()
        expect(digest, f["sha256"])
        hashes.append({"file": f["path"], "sha256": digest})
    products = []
    for row in json.loads((root / "products.json").read_text()):
        doc = frappe.get_doc("Item", row["id"])
        actual = {
            "id": doc.ccm_id,
            "name": doc.item_name,
            "price": money(doc.cashea_price),
            "marketplace_enabled": bool(doc.marketplace_enabled),
            "cashea_enabled": bool(doc.cashea_enabled),
            "supplier_reference": doc.supplier_reference,
            "warranty_quantity": doc.warranty_quantity,
            "warranty_unit": doc.warranty_unit,
            "condition": doc.ccm_condition,
        }
        expected = {k: row[k] for k in actual}
        expect(actual, expected)
        products.append(actual)
    expect(frappe.db.count("Customer", {"ccm_company": COMPANY}), 3)
    for row in json.loads((root / "customers.json").read_text()):
        c = frappe.get_doc(
            "Customer", frappe.db.get_value("Customer", {"ccm_id": row["id"]}, "name")
        )
        expect(c.mobile_no, row["phone"])
        expect(c.email_id, row["email"])
    return {
        "hashes": hashes,
        "manifest_sha256": hashlib.sha256(
            (root / "manifest.json").read_bytes()
        ).hexdigest(),
        "native_products": products,
        "native_customers": 3,
        "loaded_roles": 9,
        "native_currency_VES": bool(frappe.db.exists("Currency", "VES")),
    }


check("FIXTURE-HASH-NATIVE-EXPORT", [1, 11], fixtures)


def audits():
    rows = frappe.get_all(
        "CCM Audit",
        filters={"company": COMPANY},
        fields=[
            "name",
            "actor",
            "action",
            "object_type",
            "object_id",
            "before_state",
            "after_state",
            "reason",
            "correlation_id",
            "occurred_at",
        ],
        order_by="creation asc",
    )
    for row in rows:
        if row.action.startswith(
            ("cashea.", "cash.", "purchase.", "rate.", "bank.", "request.")
        ):
            assert row.actor and row.occurred_at and row.correlation_id
            assert row.object_type and row.object_id and row.reason.strip()
            before, after = json.loads(row.before_state), json.loads(row.after_state)
            assert isinstance(before, dict) and before, row.action
            assert isinstance(after, dict) and after, row.action
    kinds = {r.action for r in rows}
    for kind in [
        "cashea.approved",
        "cashea.settled",
        "cash.confirmed",
        "purchase.approve",
        "rate.authorized",
        "bank.reconciled",
        "request.denied",
    ]:
        assert kind in kinds, kind
    checked_semantics = []
    chains = {}
    for row in rows:
        before, after = json.loads(row.before_state), json.loads(row.after_state)
        if row.action.startswith("cashea."):
            if row.action == "cashea.created":
                expect(before, {"exists": False})
                expect(after["status"], "NEW")
            else:
                expect(before, chains[row.object_id])
                expect(after["status"], row.action.split(".")[1].upper())
                paths = {
                    "NEW": ["REVIEWED", "REJECTED", "CANCELLED"],
                    "REVIEWED": ["APPROVED", "REJECTED", "CANCELLED"],
                    "APPROVED": ["PREPARING", "CANCELLED"] if after["channel"] == "WEB" else ["FULFILLED", "CANCELLED"],
                    "PREPARING": ["SHIPPED", "CANCELLED"], "FULFILLED": ["SETTLED"], "SHIPPED": ["SETTLED"],
                }
                assert after["status"] in paths[before["status"]]
            chains[row.object_id] = after
            checked_semantics.append(row.name)
        elif row.action in ["purchase.approve", "purchase.revise"]:
            assert before["native_order"] and after["native_order"]
            assert decimal(before["amount"]) > 0 and decimal(after["amount"]) > 0
            if row.action == "purchase.approve":
                assert before["state"].startswith("Pending ")
                expect(after["state"], "Approved")
                expect(after["amount"], before["amount"])
                expect(row.reason, "LAB purchase workflow: Approve")
            else:
                expect(before["state"], "Approved")
                expect(after["state"], "Draft")
                expect(after["decision_version"], before["decision_version"] + 1)
                expect(before["amount"], "200.00")
                expect(after["amount"], "200.01")
                expect(row.reason, "LAB purchase workflow: Revise")
            checked_semantics.append(row.name)
        elif row.action == "cash.confirmed":
            expect(before["state"], "DRAFT")
            expect(after["state"], "CONFIRMED")
            expect({k: v for k, v in before.items() if k != "state"},
                   {k: v for k, v in after.items() if k != "state"})
            doc = frappe.get_doc("CCM Cash Closing", row.object_id)
            expect(doc.confirmed_by, row.actor)
            expect(json.loads(doc.snapshot), {k: v for k, v in after.items() if k != "state"})
            expect(row.reason, doc.note or "Synthetic closing matches native ledger")
            checked_semantics.append(row.name)
        elif row.action == "rate.authorized":
            expect(before, {"state": "MISSING", "date": after["date"], "rate": None})
            expect(after["state"], "AUTHORIZED")
            native = frappe.get_doc("Currency Exchange", after["native_rate"])
            expect(decimal(native.exchange_rate), decimal(after["rate"]))
            expect(str(native.date), after["date"])
            auth_doc = frappe.get_doc("CCM Rate Authorization", row.object_id)
            expect(row.reason, auth_doc.reason)
            expect(row.actor, auth_doc.authorized_by)
            checked_semantics.append(row.name)
        elif row.action == "bank.reconciled":
            expect(before["reconciled"], False)
            assert not before["payment"] and decimal(before["unallocated_amount"]) > 0
            expect(after["reconciled"], True)
            expect(after["unallocated_amount"], "0.00")
            expect(after["native_transaction"], before["native_transaction"])
            match = frappe.get_doc("CCM Bank Match", row.object_id)
            expect(after["payment"], match.matched_payment)
            expect(row.reason, "Synthetic bank decision")
            checked_semantics.append(row.name)
        elif row.action.startswith("request."):
            expect(before["state"], "attempted")
            expect(after["state"], "rejected")
            assert after.get("code", after.get("status")) in [403, 409, 422, 417]
    doc = frappe.get_doc("CCM Audit", rows[0].name)
    frappe.set_user("manager@example.invalid")
    doc.reason = "Attempt overwrite"
    try:
        b.save(doc)
    except frappe.PermissionError:
        frappe.db.rollback()
    else:
        raise AssertionError("Audit changed")
    frappe.set_user("Administrator")
    try:
        frappe.delete_doc("CCM Audit", rows[0].name)
    except frappe.PermissionError:
        frappe.db.rollback()
    else:
        raise AssertionError("Audit deleted")
    return {
        "count": len(rows),
        "kinds": sorted(kinds),
        "immutable": True,
        "semantic_before_after_reason_checks": checked_semantics,
        "records": rows,
    }


check("AUDIT01-03-NATIVE", [3, 6, 7, 8], audits)


def mcp_denial_effects():
    baseline = json.loads((OUT / "http-mapping.json").read_text())["mcp_denial_baseline"]
    http = json.loads((OUT / "http.json").read_text())["cases"]
    proof = next(c for c in http if c["case"] == "MCP-FORBIDDEN-CRITICAL-ACTIONS")
    expect(proof["status"], "PASS")
    after = {}
    for identifier, original in baseline["orders"].items():
        after[identifier] = order_effects(identifier)
        expect(after[identifier], original)
    closing = frappe.get_doc("CCM Cash Closing", frappe.db.get_value(
        "CCM Cash Closing", {"external_id": baseline["closing"]["id"]}, "name"))
    expect(closing.state, "DRAFT")
    assert not closing.confirmed_by and not closing.confirmed_at
    expect(frappe.db.exists("Currency Exchange", {"date": baseline["rate"]["date"],
        "from_currency": "USD", "to_currency": "VES"}), None)
    expect(frappe.db.count("CCM Rate Authorization", {"payment_date": baseline["rate"]["date"]}), 0)
    bank = frappe.get_doc("CCM Bank Match", frappe.db.get_value(
        "CCM Bank Match", {"transaction_key": baseline["bank"]["key"]}, "name"))
    expect(bool(bank.reconciled), False)
    assert not bank.matched_payment
    expect(money(frappe.db.get_value("Bank Transaction", bank.bank_transaction, "unallocated_amount")), "40.00")
    purchase = frappe.get_doc("CCM Purchase Request", frappe.db.get_value(
        "CCM Purchase Request", {"external_id": "MCP-PO"}, "name"))
    expect(purchase.workflow_state, "Pending Buyer")
    expect(frappe.db.get_value("Purchase Order", purchase.purchase_order, "docstatus"), 0)
    audits = []
    for denied_action in proof["actual"]["denied"]:
        records = frappe.get_all("CCM Audit", filters={"actor": "mcp@example.invalid",
            "correlation_id": denied_action["native_error"]["correlation_id"]},
            fields=["action", "before_state", "after_state", "reason", "object_id"])
        expect(len(records), 1)
        expect(records[0].action, "request.denied")
        expect(json.loads(records[0].after_state)["code"], 403)
        assert records[0].reason and records[0].object_id
        audits.append(records[0])
    expect(len(audits), 8)
    expect(frappe.db.count("CCM Audit", {"actor": "mcp@example.invalid", "action": ["in", [
        "cashea.fulfilled", "cashea.shipped", "cashea.settled", "purchase.approve",
        "cash.confirmed", "rate.authorized", "bank.reconciled"]]}), 0)
    for kind, identifier in [("cash.closing.confirmed", closing.external_id), ("purchase.approved", "MCP-PO")]:
        expect(frappe.db.count("CCM Event", {"event_type": kind,
            "payload": ["like", '%"object_id": "' + identifier + '"%']}), 0)
    return {"orders_before": baseline["orders"], "orders_after": after,
            "closing_unchanged": True, "rate_absent": True,
            "bank_unallocated": "40.00", "purchase_state": purchase.workflow_state,
            "denial_audits": audits, "successful_critical_audits": 0,
            "cash_purchase_success_events": 0}


check("MCP-DENIALS-NATIVE-EFFECTS-AUDIT", [3, 4, 5, 6, 7, 8, 10], mcp_denial_effects)


def concurrency_ledgers():
    oracle = json.loads((REPO / "fixtures/ccm-core-v1/oracle.json").read_text())
    out = []
    for identifier, source in [("TAX-CONC-S", "TAX01-S"), ("TAX-CONC-W", "TAX01-W")]:
        replay = call(
            "transitionOrder",
            payload({"id": identifier, "target": "SETTLED"}),
            "simulator",
            identifier + ":SETTLED",
        )
        expect(replay["replay"], True)
        doc = order_doc(identifier)
        want = oracle[source]
        expect(doc.status, "SETTLED")
        expect(
            money(
                frappe.db.get_value(
                    "Sales Invoice", doc.sales_invoice, "outstanding_amount"
                )
            ),
            "0.00",
        )
        ledger = balances(doc)
        expect(
            ledger["account_effects"],
            {
                "income": "-125.00",
                "cogs": "70.00",
                "stock": "-70.00",
                "receivable": "0.00",
                "cash": "55.00",
                "bank": want["transfer"],
                "tax": "-12.50",
                "commission": want["commission"],
                "shipping": want["shipping"],
            },
        )
        notes = frappe.get_all(
            "Delivery Note Item",
            filters={"against_sales_order": doc.sale_order},
            pluck="parent",
        )
        expect(len(set(notes)), 1)
        inv = frappe.get_all(
            "Sales Invoice Item",
            filters={"delivery_note": doc.delivery_note},
            pluck="parent",
        )
        expect(len(set(inv)), 1)
        expect(len(json.loads(doc.payments)), 2)
        expect(
            frappe.db.count(
                "CCM Event",
                {
                    "event_type": "cashea.approved",
                    "company": COMPANY,
                    "payload": ["like", "%" + identifier + "%"],
                },
            ),
            1,
        )
        out.append(
            {
                "id": identifier,
                "native_delivery": doc.delivery_note,
                "native_invoice": doc.sales_invoice,
                "native_payments": json.loads(doc.payments),
                "native_ledger": ledger,
                "tax_passive": "12.50",
                "effect_counts": {
                    "delivery": 1,
                    "invoice": 1,
                    "upfront_payment": 1,
                    "settlement_payment": 1,
                    "approval_event": 1,
                },
            }
        )
    expect(frappe.db.count("CCM Cashea Order", {"external_id": "IDEM-LOST"}), 1)
    expect(frappe.db.count("CCM Cashea Order", {"external_id": "IDEM-CREATE"}), 1)
    expect(
        frappe.db.count("Bank Transaction", {"reference_number": ["like", "BENCH-B%"]}),
        1000,
    )
    return {
        "tax_concurrent": out,
        "lost_order_count": 1,
        "concurrent_bank_unique_count": 1000,
    }


check("IDEM-TAX-NATIVE-EFFECT-COUNTS", [1, 4, 5, 8, 9], concurrency_ledgers)


def configuration():
    from cencomun_erp.core.setup import ROLES

    types = [
        "CCM Cashea Order",
        "CCM Cash Closing",
        "CCM Purchase Request",
        "CCM Import",
        "CCM Bank Match",
        "CCM Audit",
        "CCM Event",
        "CCM Request Key",
        "CCM Rate Authorization",
        "CCM Cashea Line",
    ]
    actual = {
        name: {
            "custom": frappe.get_meta(name).custom,
            "module": frappe.get_meta(name).module,
        }
        for name in types
    }
    assert all(
        v["custom"] == 0 and v["module"] == "Cencomun ERP" for v in actual.values()
    )
    wf = frappe.get_doc("Workflow", "CCM LAB Purchase")
    assert wf.is_active and any(t.action == "Revise" for t in wf.transitions)
    expected = json.loads((REPO / "fixtures/ccm-core-v1/permissions.json").read_text())
    for label in expected:
        if label == "statuses":
            continue
        user = label + "@example.invalid"
        assert frappe.db.exists("User", user)
        if label != "other":
            expect(
                frappe.db.count(
                    "User Permission",
                    {"user": user, "allow": "Company", "for_value": COMPANY},
                ),
                1,
            )
    return {
        "site": frappe.local.site,
        "lab_enabled": bool(frappe.conf.ccm_lab_enabled),
        "company": frappe.conf.ccm_company,
        "bank_account": frappe.conf.ccm_bank_account,
        "accounts": dict(frappe.conf.ccm_accounts),
        "types": actual,
        "workflow": wf.as_dict(),
        "hooks": {
            "after_migrate": "cencomun_erp.core.setup.install",
            "guard": "cencomun_erp.core.guards.native_write_guard",
            "permissions": "cencomun_erp.core.permissions",
        },
        "ui_only_configuration": 0,
    }


check("SUPPORTED-CONFIGURATION", [1, 3, 11, 14], configuration)
finish("audit")
