"""Native purchasing/workflow, cash ledger and bank reconciliation integration."""

import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from support import *


def purchasing():
    data = json.loads((REPO / "fixtures/ccm-core-v1/purchases.json").read_text())
    actual = []
    extra = json.loads((REPO / "fixtures/ccm-core-v1/scenarios.json").read_text())[
        "purchases_extra"
    ]
    for row in data + extra:
        p = payload(
            {
                "id": row["id"],
                "amount": row["amount"],
                **{
                    k: row[k]
                    for k in ["currency", "request_rate", "charges"]
                    if k in row
                },
            }
        )
        created = call("createPurchaseDraft", p)
        expect(created["state"], "Draft")
        expect(created["approval_amount"], row.get("expected_base", row["amount"]))
        requested = call(
            "purchaseAction",
            payload({"id": row["id"], "action": "Request Approval"}),
            "operator",
            row["id"] + ":request",
        )
        role = (row.get("role") or row["required_role"]).lower()
        expect(requested["state"], "Pending " + role.title())
        denied(
            "purchaseAction",
            payload({"id": row["id"], "action": "Approve"}),
            "operator",
            403,
            row["id"] + ":denied",
        )
        if role in ["manager", "director"]:
            denied(
                "purchaseAction",
                payload({"id": row["id"], "action": "Approve"}),
                "buyer",
                403,
                row["id"] + ":buyer-denied",
            )
        if role == "director":
            denied(
                "purchaseAction",
                payload({"id": row["id"], "action": "Approve"}),
                "manager",
                403,
                row["id"] + ":manager-denied",
            )
        result = call(
            "purchaseAction",
            payload({"id": row["id"], "action": "Approve"}),
            role,
            row["id"] + ":approve",
        )
        expect(result["state"], "Approved")
        expect(
            frappe.db.get_value("Purchase Order", result["native_order"], "docstatus"),
            1,
        )
        expect(
            call(
                "purchaseAction",
                payload({"id": row["id"], "action": "Approve"}),
                role,
                row["id"] + ":approve",
            )["replay"],
            True,
        )
        actual.append(result)
    return actual


check("PO01-09-NATIVE", [1, 3, 7], purchasing)


def purchase_change():
    p = payload({"id": "PO02", "action": "Revise", "amount": "200.01"})
    r = call("purchaseAction", p, "operator", "PO02:revise")
    expect(r["state"], "Draft")
    expect(r["approval_amount"], "200.01")
    r = call(
        "purchaseAction",
        payload({"id": "PO02", "action": "Request Approval"}),
        "operator",
        "PO02:rerequest",
    )
    expect(r["state"], "Pending Manager")
    denied(
        "purchaseAction",
        payload({"id": "PO02", "action": "Approve"}),
        "buyer",
        403,
        "PO02:rerequest-denied",
    )
    r = call(
        "purchaseAction",
        payload({"id": "PO02", "action": "Approve"}),
        "manager",
        "PO02:reapprove",
    )
    expect(r["state"], "Approved")
    p = payload({"id": "PO-SELF", "amount": "199.99"})
    call("createPurchaseDraft", p, "selfbuyer", "po-self-create")
    call(
        "purchaseAction",
        payload({"id": "PO-SELF", "action": "Request Approval"}),
        "selfbuyer",
        "po-self-request",
    )
    denied(
        "purchaseAction",
        payload({"id": "PO-SELF", "action": "Approve"}),
        "selfbuyer",
        403,
        "po-self-approve",
    )
    for amount in ["0.00", "-1.00"]:
        denied(
            "createPurchaseDraft",
            payload({"id": "PO-INVALID-" + amount, "amount": amount}),
            "operator",
            422,
            "po-invalid-" + amount,
        )
    return r


check("PO07-09-REVISION-SELF", [3, 7], purchase_change)


def journal(channel, amount, index):
    frappe.set_user("Administrator")
    accounts = {"USD": "cash", "VES": "cash_ves", "POS": "pos", "TRANSFER": "transfer"}
    ref = "Core cash " + channel + " " + str(index)
    existing = frappe.db.get_value(
        "Journal Entry", {"user_remark": ref, "docstatus": 1}, "name"
    )
    if existing:
        return existing
    n = decimal(amount)
    rate = decimal(".025") if channel == "VES" else decimal(1)
    base = abs(n) * rate
    cc = frappe.db.get_value("Company", COMPANY, "cost_center")
    doc = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "company": COMPANY,
            "posting_date": "2026-10-01",
            "multi_currency": 1,
            "user_remark": ref,
            "accounts": [
                {
                    "account": b.account(COMPANY, accounts[channel]),
                    "account_currency": "VES" if channel == "VES" else "USD",
                    "exchange_rate": float(rate),
                    "debit_in_account_currency": float(max(n, 0)),
                    "credit_in_account_currency": float(max(-n, 0)),
                    "cost_center": cc,
                },
                {
                    "account": b.account(COMPANY, "income"),
                    "exchange_rate": 1,
                    "debit_in_account_currency": float(base if n < 0 else 0),
                    "credit_in_account_currency": float(base if n > 0 else 0),
                    "cost_center": cc,
                },
            ],
        }
    )
    return b.post(doc).name


def cash():
    spec = json.loads((REPO / "fixtures/ccm-core-v1/cash.json").read_text())
    channels = []
    for ch, values in spec["source_movements"].items():
        channels.append(
            {
                "channel": ch,
                "account": b.account(
                    COMPANY,
                    {
                        "USD": "cash",
                        "VES": "cash_ves",
                        "POS": "pos",
                        "TRANSFER": "transfer",
                    }[ch],
                ),
                "vouchers": [journal(ch, a, i) for i, a in enumerate(values)],
            }
        )
    frappe.set_user("Administrator")
    invoice = frappe.db.get_value(
        "Sales Invoice", {"po_no": "CASH-PENDING", "docstatus": 1}, "name"
    )
    if not invoice:
        doc = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "company": COMPANY,
                "customer": frappe.db.get_value("Customer", {"ccm_id": "C001"}, "name"),
                "currency": "USD",
                "conversion_rate": 1,
                "selling_price_list": "Standard Selling",
                "price_list_currency": "USD",
                "plc_conversion_rate": 1,
                "posting_date": "2026-10-01",
                "set_posting_time": 1,
                "po_no": "CASH-PENDING",
                "disable_rounded_total": 1,
                "update_stock": 0,
                "items": [
                    {
                        "item_code": "P001",
                        "qty": 2,
                        "rate": 50,
                        "income_account": b.account(COMPANY, "income"),
                        "expense_account": b.account(COMPANY, "cogs"),
                    },
                    {
                        "item_code": "P002",
                        "qty": 1,
                        "rate": 25,
                        "income_account": b.account(COMPANY, "income"),
                        "expense_account": b.account(COMPANY, "cogs"),
                    },
                ],
            }
        )
        invoice = b.post(doc).name
    frappe.db.commit()
    results = []
    for row in spec["cases"]:
        p = payload(
            {
                "id": row["id"],
                "channels": [
                    {**ch, "observed": row["observed"][ch["channel"]]}
                    for ch in channels
                ],
                "pending_invoices": [invoice],
            }
        )
        result = call("createClosing", p)
        expect(result["state"], "DRAFT")
        expect(
            {x["channel"]: x["difference"] for x in result["channels"]},
            row["differences"],
        )
        expect(result["cashea_pending"], "125.00")
        expect(result["cashea_received"], "0.00")
        denied(
            "confirmClosing",
            payload({"id": row["id"]}),
            "operator",
            403,
            row["id"] + ":deny",
        )
        if row["id"] == "CS001":
            denied(
                "confirmClosing",
                payload({"id": row["id"]}),
                "manager",
                422,
                row["id"] + ":no-note",
            )
        conf = payload(
            {
                "id": row["id"],
                "note": "Synthetic difference acknowledged"
                if row["id"] == "CS001"
                else "",
            }
        )
        r = call("confirmClosing", conf, "manager", row["id"] + ":confirm")
        expect(r["state"], "CONFIRMED")
        expect(
            call("confirmClosing", conf, "manager", row["id"] + ":confirm")["replay"],
            True,
        )
        name = frappe.db.get_value(
            "CCM Cash Closing", {"external_id": row["id"]}, "name"
        )
        doc = frappe.get_doc("CCM Cash Closing", name)
        snapshot = doc.snapshot
        actor = doc.confirmed_by
        stamp = str(doc.confirmed_at)
        doc.note = "Attempt silent edit"
        try:
            b.save(doc)
        except frappe.ValidationError:
            frappe.db.rollback()
        else:
            raise AssertionError("Confirmed closing changed")
        doc.reload()
        expect(doc.snapshot, snapshot)
        expect(doc.confirmed_by, actor)
        expect(str(doc.confirmed_at), stamp)
        results.append(
            {
                **r,
                "confirmed_by": actor,
                "confirmed_at": stamp,
                "immutable": True,
                "native_sources": channels,
            }
        )
    return results


check("CASH00-06-NATIVE", [1, 3, 5, 6], cash)


def book():
    frappe.set_user("Administrator")
    customer = frappe.db.get_value("Customer", {"ccm_id": "CBANK"}, "name")
    results = []
    for row in json.loads((REPO / "fixtures/ccm-core-v1/bank-book.json").read_text()):
        existing = frappe.db.get_value(
            "Payment Entry", {"reference_no": row["reference"], "docstatus": 1}, "name"
        )
        if not existing:
            doc = frappe.get_doc(
                {
                    "doctype": "Payment Entry",
                    "payment_type": "Receive",
                    "company": COMPANY,
                    "posting_date": row["date"],
                    "party_type": "Customer",
                    "party": customer,
                    "paid_from": b.account(COMPANY, "receivable"),
                    "paid_to": b.account(COMPANY, "bank"),
                    "paid_amount": float(decimal(row["amount"])),
                    "received_amount": float(decimal(row["amount"])),
                    "source_exchange_rate": 1,
                    "target_exchange_rate": 1,
                    "reference_no": row["reference"],
                    "reference_date": row["date"],
                }
            )
            existing = b.post(doc).name
        results.append({"functional": row["id"], "native": existing})
    frappe.db.commit()
    return results


check("BANK-BOOK-FIXTURE", [1, 11], book)


def banking():
    content = (REPO / "fixtures/ccm-core-v1/bank.csv").read_text()
    p = payload({"id": "BANK01", "account_id": "BANK-USD-001", "csv": content})
    r = call("importBank", p, "operator", "bank:first")
    expect((r["rows"], r["created"], r["duplicates"]), (5, 4, 1))
    expect(
        [x["classification"] for x in r["results"]],
        ["EXACT", "PROBABLE", "AMBIGUOUS", "DUPLICATE", "UNMATCHED"],
    )
    expect(call("importBank", p, "operator", "bank:first")["replay"], True)
    alternate = payload(
        {"id": "BANK-REIMPORT", "account_id": "BANK-USD-001", "csv": content + "\n"}
    )
    second = call("importBank", alternate, "operator", "bank:alternate")
    expect(second["created"], 0)
    expect(second["duplicates"], 5)
    for row in r["results"]:
        if row["classification"] not in ["PROBABLE", "AMBIGUOUS"]:
            continue
        candidate = row["candidates"][0]
        if row["classification"] == "AMBIGUOUS":
            candidate = next(
                x
                for x in row["candidates"]
                if frappe.db.get_value("Payment Entry", x, "reference_no")
                == "AMB-BOOK-A"
            )
        p = payload(
            {
                "id": "MANUAL-" + row["classification"],
                "key": row["key"],
                "payment": candidate,
                "reason": "Synthetic bank decision",
            }
        )
        denied(
            "reconcileBank", p, "operator", 403, "bank:deny:" + row["classification"]
        )
        call("reconcileBank", p, "manager", "bank:manual:" + row["classification"])
    expect(frappe.db.count("CCM Bank Match", {"company": COMPANY, "reconciled": 1}), 3)
    signed = "account,date,reference,currency,amount,description\nBANK-USD-001,2026-10-04,NEG-001,USD,-10.00,Synthetic debit\n"
    negative = call(
        "importBank",
        payload({"id": "BANK-SIGNED", "account_id": "BANK-USD-001", "csv": signed}),
        "operator",
        "bank:signed",
    )
    native = frappe.get_doc(
        "Bank Transaction", negative["results"][0]["native_transaction"]
    )
    expect(money(native.withdrawal), "10.00")
    expect(money(native.deposit), "0.00")
    return {
        "first_import": r,
        "alternate_import": second,
        "reconciled": 3,
        "negative_native": {
            "deposit": money(native.deposit),
            "withdrawal": money(native.withdrawal),
        },
    }


check("BANK01-05-NATIVE", [1, 3, 8], banking)
finish("finance")
