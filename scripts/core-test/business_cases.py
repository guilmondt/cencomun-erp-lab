"""Real Frappe/ERPNext business integration scenarios; each case is independent."""

import sys, json, copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from support import *

ORACLE = json.loads((REPO / "fixtures/ccm-core-v1/oracle.json").read_text())
ORDERS = json.loads((REPO / "fixtures/ccm-core-v1/orders.json").read_text())


def economic(data):
    case = data["id"]
    wh = warehouse(case)
    p = payload(data, wh)
    want = ORACLE[case]
    initial = [b.stock(i, wh) for i in ["P001", "P002", "P003"]]
    existing = frappe.db.get_value(
        "CCM Cashea Order", {"external_id": case}, "delivery_note"
    )
    if not existing:
        expect([int(x.actual_qty) for x in initial], [5, 5, 5])
        expect(money(sum(decimal(x.stock_value) for x in initial)), "500.00")
    result = call("createCasheaOrder", p)
    for k in [
        "gross",
        "revenue",
        "tax",
        "commission",
        "cost",
        "net",
        "indicator",
        "accounting_profit",
    ]:
        expect(result[k], want[k])
    expect(call("createCasheaOrder", p)["replay"], True)
    for target in ["REVIEWED", "APPROVED"]:
        call(
            "transitionOrder",
            payload({"id": case, "target": target}),
            "simulator",
            case + ":" + target,
        )
    physical = "SHIPPED" if data["channel"] == "WEB" else "FULFILLED"
    if physical == "SHIPPED":
        call(
            "transitionOrder",
            payload({"id": case, "target": "PREPARING"}),
            "operator",
            case + ":PREPARING",
        )
    call(
        "transitionOrder",
        payload({"id": case, "target": physical}),
        "operator",
        case + ":" + physical,
    )
    doc = order_doc(case)
    invoice = frappe.get_doc("Sales Invoice", doc.sales_invoice)
    expect(money(invoice.grand_total), want["gross"])
    expect(money(invoice.outstanding_amount), want["gross"])
    expect(money(invoice.net_total), want["revenue"])
    expect(money(invoice.total_taxes_and_charges), want["tax"])
    actual = [b.stock(i, wh) for i in ["P001", "P002", "P003"]]
    expect([int(x.actual_qty) for x in actual], want["stock"])
    expect(money(sum(decimal(x.stock_value) for x in actual)), want["stock_value"])
    result = call(
        "transitionOrder",
        payload({"id": case, "target": "SETTLED"}),
        "simulator",
        case + ":SETTLED",
    )
    expect(
        call(
            "transitionOrder",
            payload({"id": case, "target": "SETTLED"}),
            "simulator",
            case + ":SETTLED",
        )["replay"],
        True,
    )
    denied(
        "transitionOrder",
        payload({"id": case, "target": "CANCELLED"}),
        "simulator",
        409,
        case + ":late-cancel",
    )
    doc = order_doc(case)
    ledger = balances(doc)
    expected = {
        "income": money(-decimal(want["revenue"])),
        "cogs": want["cost"],
        "stock": money(-decimal(want["cost"])),
        "receivable": "0.00",
        "cash": want["upfront"],
        "bank": want["transfer"],
        "tax": money(-decimal(want["tax"])),
        "commission": want["commission"],
        "shipping": want["shipping"],
    }
    expect(ledger["account_effects"], expected)
    expect(
        money(
            frappe.db.get_value(
                "Sales Invoice", doc.sales_invoice, "outstanding_amount"
            )
        ),
        "0.00",
    )
    native_payments = [
        frappe.get_doc("Payment Entry", x) for x in json.loads(doc.payments)
    ]
    expect(
        [money(x.references[0].allocated_amount) for x in native_payments],
        [want["upfront"], data["financed_amount"]],
    )
    invoice_lines = [
        {
            "item": r.item_code,
            "gross": money(r.amount),
            "base": money(r.net_amount),
            "tax": money(decimal(r.amount) - decimal(r.net_amount)),
        }
        for r in invoice.items
    ]
    if case.startswith("TAX"):
        expect(
            invoice_lines,
            [
                {"item": "P001", "gross": "110.00", "base": "100.00", "tax": "10.00"},
                {"item": "P002", "gross": "27.50", "base": "25.00", "tax": "2.50"},
            ],
        )
    return {
        "expected": want,
        "order": result,
        "warehouse": wh,
        "native_invoice": invoice.name,
        "invoice_lines": invoice_lines,
        "ledger": ledger,
        "payment_allocations": [
            money(x.references[0].allocated_amount) for x in native_payments
        ],
        "final_customer_balance": "0.00",
    }


for data in ORDERS:
    check(data["id"] + "-NATIVE", [1, 3, 4, 5, 11], lambda data=data: economic(data))


def product_fields():
    frappe.set_user("operator@example.invalid")
    item = frappe.get_doc("Item", "P001")
    original = item.as_dict()
    actual = []
    for q, u in [
        (30, "DAY"),
        (6, "MONTH"),
        (1, "YEAR"),
        (0, "DAY"),
        (0, "MONTH"),
        (0, "YEAR"),
    ]:
        item.warranty_quantity = q
        item.warranty_unit = u
        item.save()
        item.reload()
        expect((item.warranty_quantity, item.warranty_unit), (q, u))
        actual.append([q, u])
    item.cashea_enabled = 0
    item.save()
    expect(money(item.cashea_price), "50.00")
    item.cashea_enabled = 1
    item.warranty_quantity = 12
    item.warranty_unit = "MONTH"
    item.save()
    frappe.db.commit()
    return {
        "warranties": actual,
        "retained_disabled_price": "50.00",
        "native_fields": [
            "marketplace_enabled",
            "cashea_enabled",
            "cashea_price",
            "supplier_reference",
            "warranty_quantity",
            "warranty_unit",
            "ccm_condition",
        ],
    }


check("PROD01-04", [1, 5, 11], product_fields)


def negatives():
    wh = warehouse("VAL")
    p = payload({**ORDERS[0], "id": "VAL"}, wh)
    observed = []
    changes = [
        ("quantity", {"qty": "0"}),
        ("fractional", {"qty": "0.5"}),
        ("negative", {"qty": "-1"}),
        ("price-zero", {"unit_price": "0"}),
        ("price-negative", {"unit_price": "-1"}),
        ("price-precision", {"unit_price": "0.005"}),
        ("disabled", {"product_id": "P003"}),
    ]
    for label, values in changes:
        bad = copy.deepcopy(p)
        bad["id"] = "VAL-" + label
        bad["lines"][0].update(values)
        r = denied("createCasheaOrder", bad, "operator", 422, label)
        observed.append({"case": label, "code": r["status"]})
    for financed in ["-1", "125.01"]:
        bad = copy.deepcopy(p)
        bad["id"] = "VAL-finance-" + financed
        bad["financed_amount"] = financed
        denied("createCasheaOrder", bad, "operator", 422, bad["id"])
    expect(frappe.db.count("CCM Cashea Order", {"external_id": ["like", "VAL-%"]}), 0)
    # Native stock validation must reject negative valuation before any ledger effect.
    frappe.set_user("Administrator")
    doc = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "company": COMPANY,
            "stock_entry_type": "Material Receipt",
            "purpose": "Material Receipt",
            "posting_date": "2026-10-01",
            "items": [
                {
                    "item_code": "P001",
                    "qty": 1,
                    "t_warehouse": wh,
                    "basic_rate": -1,
                    "expense_account": b.account(COMPANY, "opening"),
                }
            ],
        }
    )
    try:
        b.post(doc)
    except frappe.ValidationError as e:
        observed.append(
            {"case": "negative-native-cost", "code": 422, "native_error": str(e)}
        )
        frappe.db.rollback()
    else:
        raise AssertionError("Negative native cost was accepted")
    expect(
        [int(b.stock(i, wh).actual_qty) for i in ["P001", "P002", "P003"]], [5, 5, 5]
    )
    return observed


check("VAL01-04", [4, 5], negatives)


def states():
    wh = warehouse("STATE")
    outputs = []
    for channel in ["STORE", "WEB"]:
        for target in ["REJECTED", "CANCELLED"]:
            p = payload(
                {
                    **ORDERS[0],
                    "id": "STATE-" + channel + "-" + target,
                    "channel": channel,
                },
                wh,
            )
            call("createCasheaOrder", p)
            denied(
                "transitionOrder",
                payload({"id": p["id"], "target": "SETTLED"}),
                "simulator",
                409,
                p["id"] + ":skip",
            )
            r = call(
                "transitionOrder",
                payload({"id": p["id"], "target": target}),
                "simulator",
                p["id"] + ":" + target,
            )
            expect(r["status"], target)
            outputs.append(r)
    expect(
        [int(b.stock(i, wh).actual_qty) for i in ["P001", "P002", "P003"]], [5, 5, 5]
    )
    return outputs


check("STATE01-04", [3, 4], states)


def insufficient():
    wh = warehouse("INV")
    p = payload(
        {
            **ORDERS[0],
            "id": "INV-INSUFFICIENT",
            "lines": [{"product_id": "P001", "qty": "6", "unit_price": "50.00"}],
        },
        wh,
    )
    call("createCasheaOrder", p)
    for target in ["REVIEWED", "APPROVED"]:
        call(
            "transitionOrder",
            payload({"id": p["id"], "target": target}),
            "simulator",
            p["id"] + ":" + target,
        )
    denied(
        "transitionOrder",
        payload({"id": p["id"], "target": "FULFILLED"}),
        "operator",
        422,
        p["id"] + ":FULFILLED",
    )
    doc = order_doc(p["id"])
    expect(doc.status, "APPROVED")
    expect(bool(doc.delivery_note or doc.sales_invoice), False)
    expect(int(b.stock("P001", wh).actual_qty), 5)
    return {
        "state": doc.status,
        "stock": 5,
        "delivery_note": None,
        "sales_invoice": None,
    }


check("INV01-03-INSUFFICIENT", [4, 5], insufficient)


def fx():
    outputs = []
    for identifier, day, lines, want in [
        ("FX01", "2026-10-01", ["1.00"], "40.00"),
        ("FX02", "2026-10-02", ["1.00"], "41.00"),
    ]:
        p = payload({"id": identifier, "date": day, "lines": lines})
        r = call("currencyPayment", p)
        expect(r["total"], want)
        outputs.append(r)
    missing = payload({"id": "FX-MISSING", "date": "2026-10-03", "lines": ["1.00"]})
    denied("currencyPayment", missing, "operator", 422, "fx-missing")
    rate = payload(
        {
            "id": "FX-AUTH",
            "date": "2026-10-03",
            "rate": "40.500000",
            "reason": "Synthetic authorized payment-day rate",
        }
    )
    denied("authorizeRate", rate, "operator", 403, "fx-denied")
    call("authorizeRate", rate, "manager", "fx-authorized")
    r = call(
        "currencyPayment",
        payload({"id": "MONEY-ROUND", "date": "2026-10-03", "lines": ["0.01", "0.01"]}),
    )
    expect(r["lines"], ["0.41", "0.41"])
    expect(r["total"], "0.82")
    outputs.append(r)
    return outputs


check("FX01-03-MONEY01-03", [3, 5], fx)
finish("business")
