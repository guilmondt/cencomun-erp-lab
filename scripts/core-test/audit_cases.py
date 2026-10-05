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
    for row in rows:
        if row.action in ["cash.confirmed", "rate.authorized", "bank.reconciled"]:
            assert row.object_id and row.after_state and row.reason
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
        "records": rows,
    }


check("AUDIT01-03-NATIVE", [3, 6, 7, 8], audits)


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
