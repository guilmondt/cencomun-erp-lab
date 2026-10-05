"""Native-only fixture mechanics and independent assertion recording."""

import json, time, traceback
from pathlib import Path
import frappe
from cencomun_erp.core import business as b
from cencomun_erp.core.guards import decimal, money

REPO = Path("/workspace/cencomun-erp-lab")
ROOT = Path("/workspace/.local/frappe-integral")
OUT = REPO / "reports/evidence/frappe-core"
OUT.mkdir(parents=True, exist_ok=True)
COMPANY = "CCM-LAB-001"
ABBR = "CLAB"
CASES = []


def check(identifier, criteria, fn):
    t = time.monotonic()
    try:
        actual = fn()
        CASES.append(
            {
                "case": identifier,
                "criteria": criteria,
                "status": "PASS",
                "actual": actual,
                "seconds": round(time.monotonic() - t, 4),
            }
        )
        print(identifier, "PASS", flush=True)
        return actual
    except Exception as exc:
        frappe.db.rollback()
        CASES.append(
            {
                "case": identifier,
                "criteria": criteria,
                "status": "FAIL",
                "error": type(exc).__name__ + ": " + str(exc),
                "trace": traceback.format_exc(),
                "seconds": round(time.monotonic() - t, 4),
            }
        )
        print(identifier, "FAIL", type(exc).__name__, str(exc)[:180], flush=True)
    finally:
        frappe.set_user("Administrator")


def expect(actual, expected):
    if actual != expected:
        raise AssertionError({"expected": expected, "actual": actual})
    return actual


def call(op, p, actor="operator", key=None):
    from cencomun_erp.core.api import execute

    frappe.set_user(actor + "@example.invalid")
    r = execute(op, p, key or op + ":" + p.get("id", "case"))
    if not r.get("ok"):
        raise RuntimeError(r)
    return r["result"]


def denied(op, p, actor="operator", status=403, key=None):
    from cencomun_erp.core.api import execute

    frappe.set_user(actor + "@example.invalid")
    r = execute(op, p, key or "deny:" + op + ":" + p.get("id", "case"))
    expect(r.get("status"), status)
    return r


def payload(data, warehouse=None):
    return {
        **data,
        "company_id": COMPANY,
        **({"warehouse": warehouse} if warehouse else {}),
    }


def warehouse(case):
    frappe.set_user("Administrator")
    label = "WH-LAB-001-" + case
    name = label + " - " + ABBR
    if not frappe.db.exists("Warehouse", name):
        frappe.get_doc(
            {
                "doctype": "Warehouse",
                "warehouse_name": label,
                "company": COMPANY,
                "parent_warehouse": "All Warehouses - " + ABBR,
            }
        ).insert()
    if not frappe.db.exists(
        "Stock Entry", {"remarks": "Core snapshot " + case, "docstatus": 1}
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Stock Entry",
                "company": COMPANY,
                "stock_entry_type": "Material Receipt",
                "purpose": "Material Receipt",
                "posting_date": "2026-10-01",
                "posting_time": "08:00:00",
                "set_posting_time": 1,
                "remarks": "Core snapshot " + case,
                "items": [
                    {
                        "item_code": i,
                        "qty": 5,
                        "t_warehouse": name,
                        "basic_rate": c,
                        "allow_zero_valuation_rate": 0,
                        "expense_account": b.account(COMPANY, "opening"),
                    }
                    for i, c in [("P001", 30), ("P002", 10), ("P003", 60)]
                ],
            }
        )
        b.post(doc)
        frappe.db.commit()
    return name


def order_doc(identifier):
    return frappe.get_doc(
        "CCM Cashea Order",
        frappe.db.get_value(
            "CCM Cashea Order", {"company": COMPANY, "external_id": identifier}, "name"
        ),
    )


def balances(order):
    vouchers = [order.delivery_note, order.sales_invoice] + json.loads(
        order.payments or "[]"
    )
    rows = frappe.get_all(
        "GL Entry",
        filters={"company": COMPANY, "voucher_no": ["in", vouchers], "is_cancelled": 0},
        fields=[
            "voucher_type",
            "voucher_no",
            "account",
            "debit",
            "credit",
            "debit_in_account_currency",
            "credit_in_account_currency",
            "account_currency",
        ],
    )
    sums = {}
    byvoucher = {}
    for row in rows:
        value = decimal(row.debit) - decimal(row.credit)
        sums[row.account] = sums.get(row.account, decimal(0)) + value
        byvoucher[row.voucher_no] = byvoucher.get(row.voucher_no, decimal(0)) + value
    expect({k: money(v) for k, v in byvoucher.items()}, {k: "0.00" for k in byvoucher})
    categories = {
        key: money(sums.get(b.account(COMPANY, key), decimal(0)))
        for key in [
            "income",
            "cogs",
            "stock",
            "receivable",
            "cash",
            "bank",
            "tax",
            "commission",
            "shipping",
        ]
    }
    return {
        "account_effects": categories,
        "native_gl": rows,
        "balanced_vouchers": list(byvoucher),
    }


def finish(name):
    data = {"site": frappe.local.site, "profile": "LAB-ONLY-v1", "cases": CASES}
    (OUT / (name + ".json")).write_text(json.dumps(data, indent=2, default=str) + "\n")
    print(
        "Cases:",
        len(CASES),
        "PASS:",
        sum(c["status"] == "PASS" for c in CASES),
        "FAIL:",
        sum(c["status"] == "FAIL" for c in CASES),
        flush=True,
    )
