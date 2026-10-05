"""Native purchasing, cash, bank and payment-date scenarios for LAB-ONLY-v1."""

import csv, io, json, hashlib
from datetime import date
from decimal import Decimal
import frappe
from frappe.utils import now_datetime
from cencomun_erp.core.guards import decimal, money, service
from cencomun_erp.core.business import (
    access,
    account,
    insert,
    save,
    post,
    audit,
    event,
    digest,
    quantity,
)


def create_purchase(payload):
    company = payload["company_id"]
    amount = decimal(payload["amount"])
    if amount <= 0:
        frappe.throw("Purchase amount must be positive")
    currency = payload.get("currency", "USD")
    conversion = 1
    if currency == "VES":
        conversion = float(1 / decimal(payload.get("request_rate", "40.000000")))
    elif currency != "USD":
        frappe.throw("Unsupported lab currency")
    doc = frappe.get_doc(
        {
            "doctype": "Purchase Order",
            "supplier": "SUP-LAB",
            "company": company,
            "transaction_date": "2026-10-01",
            "schedule_date": "2026-10-01",
            "currency": currency,
            "conversion_rate": conversion,
            "buying_price_list": "Standard Buying",
            "price_list_currency": currency,
            "plc_conversion_rate": conversion,
            "disable_rounded_total": 1,
            "items": [
                {
                    "item_code": "P001",
                    "qty": 1,
                    "rate": float(amount),
                    "warehouse": frappe.db.get_value(
                        "Warehouse",
                        {"company": company, "warehouse_name": "Stores"},
                        "name",
                    ),
                    "schedule_date": "2026-10-01",
                }
            ],
        }
    )
    for value in payload.get("charges", []):
        doc.append(
            "taxes",
            {
                "charge_type": "Actual",
                "account_head": account(company, "commission"),
                "description": "Synthetic purchase charge",
                "tax_amount": float(abs(decimal(value))),
                "category": "Total",
                "add_deduct_tax": "Deduct" if decimal(value) < 0 else "Add",
            },
        )
    doc = doc.insert(ignore_permissions=True)
    request = insert(
        {
            "doctype": "CCM Purchase Request",
            "company": company,
            "external_id": payload["id"],
            "purchase_order": doc.name,
            "approval_amount": money(doc.base_grand_total),
            "workflow_state": "Draft",
        }
    )
    audit(
        company,
        "purchase.draft",
        request,
        after={"native_order": doc.name, "approval_amount": request.approval_amount},
    )
    return {
        "id": request.external_id,
        "state": request.workflow_state,
        "approval_amount": request.approval_amount,
        "native_order": doc.name,
    }


def purchase_action(payload):
    from frappe.model.workflow import apply_workflow

    name = frappe.db.get_value(
        "CCM Purchase Request",
        {"company": payload["company_id"], "external_id": payload["id"]},
        "name",
    )
    if not name:
        frappe.throw("Purchase not found")
    with frappe.cache.lock("ccm-purchase:" + name, timeout=300, blocking_timeout=110):
        frappe.db.commit()
        doc = frappe.get_doc("CCM Purchase Request", name)
        before = doc.workflow_state
        action = payload["action"]
        po = frappe.get_doc("Purchase Order", doc.purchase_order)
        if action == "Approve":
            required = decimal(doc.approval_amount)
            roles = (
                ["CCM Buyer", "CCM Manager", "CCM Director"]
                if required <= 200
                else ["CCM Manager", "CCM Director"]
                if required <= 1000
                else ["CCM Director"]
            )
            access(doc.company, roles)
            if doc.owner == frappe.session.user:
                frappe.throw("Self approval denied", frappe.PermissionError)
        else:
            access(doc.company, ["CCM Operator"])
        if action == "Revise":
            new_amount = decimal(payload["amount"])
            if new_amount <= 0:
                frappe.throw("Purchase amount must be positive")
            doc = apply_workflow(doc.as_dict(), "Revise")
            if po.docstatus == 1:
                po.flags.ignore_permissions = True
                po.cancel()
                amended = frappe.copy_doc(po)
                amended.amended_from = po.name
                amended.docstatus = 0
                po = amended
            po.items[0].rate = float(new_amount)
            po.flags.ignore_permissions = True
            po = po.save(ignore_permissions=True)
            doc.purchase_order = po.name
            doc.approval_amount = money(po.base_grand_total)
            doc.decision_version += 1
            save(doc)
        else:
            doc = apply_workflow(doc.as_dict(), action)
            if action == "Approve":
                po.flags.ignore_permissions = True
                po.submit()
                event(doc.company, "purchase.approved", doc)
        audit(
            doc.company,
            "purchase." + action.lower(),
            doc,
            {"state": before},
            {"state": doc.workflow_state, "amount": doc.approval_amount},
        )
        return {
            "id": doc.external_id,
            "state": doc.workflow_state,
            "approval_amount": doc.approval_amount,
            "native_order": doc.purchase_order,
        }


def create_closing(payload):
    company = payload["company_id"]
    snapshot = []
    for row in payload["channels"]:
        acct = row["account"]
        if frappe.db.get_value("Account", acct, "company") != company:
            frappe.throw("Account company mismatch", frappe.PermissionError)
        vouchers = row.get("vouchers", [])
        entries = (
            frappe.get_all(
                "GL Entry",
                filters={
                    "company": company,
                    "account": acct,
                    "voucher_no": ["in", vouchers],
                    "is_cancelled": 0,
                },
                fields=["debit_in_account_currency", "credit_in_account_currency"],
            )
            if vouchers
            else []
        )
        expected = sum(
            decimal(e.debit_in_account_currency) - decimal(e.credit_in_account_currency)
            for e in entries
        )
        observed = decimal(row["observed"])
        snapshot.append(
            {
                "channel": row["channel"],
                "currency": frappe.db.get_value("Account", acct, "account_currency"),
                "expected": money(expected),
                "observed": money(observed),
                "difference": money(observed - expected),
                "vouchers": vouchers,
            }
        )
    pending = Decimal("0")
    for invoice in payload.get("pending_invoices", []):
        doc = frappe.get_doc("Sales Invoice", invoice)
        if doc.company != company:
            frappe.throw("Invoice company mismatch", frappe.PermissionError)
        pending += decimal(doc.outstanding_amount)
    data = {
        "channels": snapshot,
        "cashea_pending": money(pending),
        "cashea_received": "0.00",
    }
    doc = insert(
        {
            "doctype": "CCM Cash Closing",
            "company": company,
            "external_id": payload["id"],
            "snapshot": json.dumps(data),
            "state": "DRAFT",
        }
    )
    audit(company, "cash.prepared", doc, after=data)
    return {"id": doc.external_id, "state": doc.state, **data}


def confirm_closing(payload):
    name = frappe.db.get_value(
        "CCM Cash Closing",
        {"company": payload["company_id"], "external_id": payload["id"]},
        "name",
    )
    if not name:
        frappe.throw("Closing not found")
    with frappe.cache.lock("ccm-closing:" + name, timeout=60, blocking_timeout=30):
        frappe.db.commit()
        doc = frappe.get_doc("CCM Cash Closing", name)
        if doc.state != "DRAFT":
            frappe.throw("Closing already confirmed", frappe.TimestampMismatchError)
        data = json.loads(doc.snapshot)
        if any(
            decimal(c["difference"]) != 0 for c in data["channels"]
        ) and not payload.get("note"):
            frappe.throw("Difference requires a note")
        doc.state = "CONFIRMED"
        doc.note = payload.get("note")
        doc.confirmed_by = frappe.session.user
        doc.confirmed_at = now_datetime()
        save(doc)
        audit(
            doc.company,
            "cash.confirmed",
            doc,
            {"state": "DRAFT"},
            {"state": "CONFIRMED", **data},
            doc.note or "Synthetic closing matches native ledger",
        )
        event(doc.company, "cash.closing.confirmed", doc)
        return {"id": doc.external_id, "state": doc.state, **data}


def reconcile(match, payment):
    if match.reconciled:
        frappe.throw("Already reconciled", frappe.TimestampMismatchError)
    native = frappe.get_doc("Bank Transaction", match.bank_transaction)
    native.flags.ignore_permissions = True
    native.add_payment_entries(
        [{"payment_doctype": "Payment Entry", "payment_name": payment}]
    )
    native.save(ignore_permissions=True)
    if decimal(native.unallocated_amount) != 0:
        frappe.throw("Native bank allocation incomplete")
    match.reconciled = 1
    match.matched_payment = payment
    save(match)


def import_bank(payload):
    with frappe.cache.lock(
        "ccm-bank:" + digest([payload["company_id"], payload["account_id"]]),
        timeout=300,
        blocking_timeout=110,
    ):
        frappe.db.commit()
        return _import_bank(payload)


def _import_bank(payload):
    company = payload["company_id"]
    content = payload["csv"]
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    prior = frappe.db.get_value("CCM Import", {"external_id": file_hash}, "result")
    if prior:
        return json.loads(prior)
    bank_account = frappe.conf.ccm_bank_account
    rows = list(csv.DictReader(io.StringIO(content)))
    results = []
    unique = 0
    duplicates = 0
    for row in rows:
        if row["account"] != payload["account_id"] or row["currency"] != "USD":
            frappe.throw("Bank fixture account/currency mismatch")
        amount = decimal(row["amount"])
        dt = date.fromisoformat(row["date"])
        key = digest(
            [
                company,
                row["account"],
                dt.isoformat(),
                row["reference"].strip(),
                row["currency"],
                money(amount),
            ]
        )
        existing = frappe.db.get_value(
            "CCM Bank Match", {"transaction_key": key}, "name"
        )
        if existing:
            duplicates += 1
            results.append({"classification": "DUPLICATE", "key": key})
            continue
        native = post(
            frappe.get_doc(
                {
                    "doctype": "Bank Transaction",
                    "date": dt,
                    "bank_account": bank_account,
                    "currency": "USD",
                    "deposit": float(max(amount, 0)),
                    "withdrawal": float(max(-amount, 0)),
                    "reference_number": row["reference"],
                    "description": row["description"],
                }
            )
        )
        book = frappe.get_all(
            "Payment Entry",
            filters={
                "company": company,
                "docstatus": 1,
                "paid_to": account(company, "bank"),
                "reference_no": ["like", "%BOOK%"],
            },
            fields=["name", "reference_no", "posting_date", "received_amount"],
        )
        # Exact-reference fixture also belongs to the native book.
        book += frappe.get_all(
            "Payment Entry",
            filters={
                "company": company,
                "docstatus": 1,
                "paid_to": account(company, "bank"),
                "reference_no": "EXACT-001",
            },
            fields=["name", "reference_no", "posting_date", "received_amount"],
        )
        exact = [
            r
            for r in book
            if r.reference_no == row["reference"]
            and r.posting_date == dt
            and decimal(r.received_amount) == amount
        ]
        candidates = [
            r
            for r in book
            if decimal(r.received_amount) == amount
            and abs((r.posting_date - dt).days) <= 2
        ]
        classification = (
            "EXACT"
            if len(exact) == 1
            else "AMBIGUOUS"
            if len(candidates) > 1
            else "PROBABLE"
            if len(candidates) == 1
            else "UNMATCHED"
        )
        names = [r.name for r in (exact if classification == "EXACT" else candidates)]
        match = insert(
            {
                "doctype": "CCM Bank Match",
                "company": company,
                "external_id": key,
                "transaction_key": key,
                "bank_transaction": native.name,
                "classification": classification,
                "candidates": json.dumps(names),
            }
        )
        if classification == "EXACT":
            reconcile(match, names[0])
        unique += 1
        results.append(
            {
                "classification": classification,
                "key": key,
                "native_transaction": native.name,
                "reconciled": bool(match.reconciled),
                "candidates": names,
            }
        )
        audit(
            company,
            "bank.imported",
            match,
            after={
                "classification": classification,
                "reconciled": bool(match.reconciled),
            },
        )
    result = {
        "rows": len(rows),
        "created": unique,
        "duplicates": duplicates,
        "results": results,
    }
    insert(
        {
            "doctype": "CCM Import",
            "company": company,
            "external_id": file_hash,
            "file_hash": file_hash,
            "bank_account": bank_account,
            "result": json.dumps(result),
        }
    )
    return result


def reconcile_bank(payload):
    doc = frappe.get_doc(
        "CCM Bank Match",
        frappe.db.get_value(
            "CCM Bank Match",
            {"company": payload["company_id"], "transaction_key": payload["key"]},
            "name",
        ),
    )
    candidates = json.loads(doc.candidates)
    if not payload.get("reason"):
        frappe.throw("Manual bank decision requires a reason")
    if payload["payment"] not in candidates:
        frappe.throw("Not an eligible candidate")
    reconcile(doc, payload["payment"])
    audit(
        doc.company,
        "bank.reconciled",
        doc,
        after={"payment": doc.matched_payment},
        reason=payload["reason"],
    )
    return {"key": doc.transaction_key, "reconciled": True}


def authorize_rate(payload):
    rate = decimal(payload["rate"])
    if rate <= 0 or rate.as_tuple().exponent < -6:
        frappe.throw("Rate must be positive with at most six decimals")
    if not payload.get("reason"):
        frappe.throw("Manual rate requires a reason")
    if frappe.db.exists(
        "Currency Exchange",
        {"date": payload["date"], "from_currency": "USD", "to_currency": "VES"},
    ):
        frappe.throw("Date already has a rate", frappe.TimestampMismatchError)
    native = frappe.get_doc(
        {
            "doctype": "Currency Exchange",
            "date": payload["date"],
            "from_currency": "USD",
            "to_currency": "VES",
            "exchange_rate": float(rate),
            "for_buying": 1,
            "for_selling": 1,
        }
    ).insert(ignore_permissions=True)
    doc = insert(
        {
            "doctype": "CCM Rate Authorization",
            "company": payload["company_id"],
            "external_id": native.name,
            "payment_date": payload["date"],
            "rate": str(rate),
            "reason": payload["reason"],
            "authorized_by": frappe.session.user,
        }
    )
    audit(
        doc.company,
        "rate.authorized",
        doc,
        after={"date": payload["date"], "rate": str(rate)},
        reason=payload["reason"],
    )
    return {"date": payload["date"], "rate": str(rate)}


def currency_payment(payload):
    company = payload["company_id"]
    day = payload["date"]
    rate = frappe.db.get_value(
        "Currency Exchange",
        {"date": day, "from_currency": "USD", "to_currency": "VES"},
        "exchange_rate",
    )
    if not rate:
        frappe.throw("Missing payment-date rate; authorization required")
    amounts = [decimal(x) for x in payload["lines"]]
    if any(x <= 0 or x.as_tuple().exponent < -2 for x in amounts):
        frappe.throw("Invalid payment line")
    native_customer = frappe.db.get_value("Customer", {"ccm_id": "C002", "ccm_company": company}, "name")
    if not native_customer:
        frappe.throw("Payment customer outside authorized company", frappe.PermissionError)
    invoice = post(
        frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "company": company,
                "customer": native_customer,
                "currency": "USD",
                "conversion_rate": 1,
                "selling_price_list": "Standard Selling",
                "price_list_currency": "USD",
                "plc_conversion_rate": 1,
                "posting_date": day,
                "set_posting_time": 1,
                "update_stock": 0,
                "disable_rounded_total": 1,
                "items": [
                    {
                        "item_code": "P002",
                        "qty": 1,
                        "rate": float(sum(amounts)),
                        "income_account": account(company, "income"),
                        "expense_account": account(company, "cogs"),
                    }
                ],
            }
        )
    )
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    converted = []
    payments = []
    for amount in amounts:
        value = decimal(money(amount * decimal(rate)))
        pay = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "company": company,
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": native_customer,
                "posting_date": day,
                "paid_from": account(company, "receivable"),
                "paid_to": account(company, "cash_ves"),
                "paid_amount": float(amount),
                "received_amount": float(value),
                "source_exchange_rate": 1,
                "target_exchange_rate": float(1 / decimal(rate)),
                "reference_no": "FX-" + payload["id"],
                "reference_date": day,
                "references": [
                    {
                        "reference_doctype": "Sales Invoice",
                        "reference_name": invoice.name,
                        "allocated_amount": float(amount),
                        "exchange_rate": 1,
                    }
                ],
            }
        )
        payments.append(post(pay).name)
        converted.append(money(value))
    audit(
        company,
        "payment.rate_applied",
        after={
            "date": day,
            "rate": str(rate),
            "lines": converted,
            "payments": payments,
        },
    )
    return {
        "date": day,
        "rate": str(rate),
        "lines": converted,
        "total": money(sum(decimal(x) for x in converted)),
        "payments": payments,
    }
