"""LAB-only deterministic domain services using native ERP Documents.

Scoped native writes are privileged only after explicit role/company checks.
Native validation, submission, stock and accounting logic always execute.
"""

import hashlib, json
from datetime import datetime, timezone
from decimal import Decimal
import frappe
from frappe.utils import now_datetime
from cencomun_erp.core.guards import decimal, money, service

READERS = [
    "CCM Reader",
    "CCM Operator",
    "CCM Buyer",
    "CCM Manager",
    "CCM Director",
    "CCM Simulator",
    "CCM MCP",
]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def access(company, roles):
    if not frappe.conf.get("ccm_lab_enabled"):
        frappe.throw("LAB profile is not enabled", frappe.PermissionError)
    if not set(roles) & set(frappe.get_roles()):
        frappe.throw("Role denied", frappe.PermissionError)
    allowed = frappe.get_all(
        "User Permission",
        filters={"user": frappe.session.user, "allow": "Company"},
        pluck="for_value",
    )
    if company not in allowed:
        frappe.throw("Company denied", frappe.PermissionError)


def account(company, key):
    mapping = frappe.conf.get("ccm_accounts", {})
    if company != frappe.conf.get("ccm_company"):
        frappe.throw("Unconfigured lab company", frappe.PermissionError)
    return mapping[key]


def insert(data):
    with service():
        return frappe.get_doc(data).insert(ignore_permissions=True)


def save(doc):
    with service():
        return doc.save(ignore_permissions=True)


def post(doc):
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    doc.submit()
    return doc


def audit(
    company, action, obj=None, before=None, after=None, reason="", correlation=None
):
    critical = action in [
        "cash.confirmed", "purchase.approve", "purchase.revise",
        "rate.authorized", "bank.reconciled",
    ] or (action.startswith("cashea.") and action != "cashea.created")
    if critical and (
        not isinstance(before, dict) or not before
        or not isinstance(after, dict) or not after
        or not isinstance(reason, str) or not reason.strip()
    ):
        frappe.throw("Critical LAB audit requires before, after and reason")
    insert(
        {
            "doctype": "CCM Audit",
            "company": company,
            "external_id": frappe.generate_hash(length=32),
            "actor": frappe.session.user,
            "action": action,
            "object_type": obj.doctype if obj else None,
            "object_id": obj.name if obj else None,
            "before_state": json.dumps(before, default=str),
            "after_state": json.dumps(after, default=str),
            "reason": reason,
            "correlation_id": correlation
            or getattr(frappe.local, "ccm_correlation", None),
            "occurred_at": now_datetime(),
        }
    )


def event(company, kind, obj):
    eid = digest([kind, obj.doctype, obj.name, obj.get("decision_version") or 1])
    if not frappe.db.exists("CCM Event", {"external_id": eid}):
        payload = {
            "schema_version": 1,
            "event_id": eid,
            "object_id": obj.external_id,
            "company_id": company,
            "actor": frappe.session.user,
            "occurred_at": now_datetime().isoformat(),
            "correlation_id": getattr(frappe.local, "ccm_correlation", None),
            "type": kind,
        }
        insert(
            {
                "doctype": "CCM Event",
                "company": company,
                "external_id": eid,
                "event_type": kind,
                "payload": json.dumps(payload),
            }
        )


def write(operation, key, payload, roles, action):
    company = payload.get("company_id")
    access(company, roles)
    if not key:
        frappe.throw("Idempotency-Key required")
    fingerprint = digest(payload)
    scope = digest([company, operation, key])
    with frappe.cache.lock("ccm-request:" + scope, timeout=300, blocking_timeout=110):
        frappe.db.commit()  # Fresh read after acquiring the distributed lock.
        existing = frappe.db.get_value(
            "CCM Request Key",
            {"external_id": scope},
            ["payload_hash", "result"],
            as_dict=True,
        )
        if existing:
            if existing.payload_hash != fingerprint:
                frappe.throw(
                    "Idempotency payload conflict", frappe.TimestampMismatchError
                )
            return {**json.loads(existing.result), "replay": True}
        frappe.local.ccm_correlation = scope
        try:
            with service():
                result = action()
            insert(
                {
                    "doctype": "CCM Request Key",
                    "company": company,
                    "external_id": scope,
                    "operation": operation,
                    "payload_hash": fingerprint,
                    "result": json.dumps(result, default=str),
                }
            )
            frappe.db.commit()
            return {**result, "replay": False}
        except Exception:
            frappe.db.rollback()
            raise


def quantity(value):
    n = decimal(value)
    if n <= 0 or n != n.to_integral_value():
        frappe.throw("Quantity must be a positive whole unit")
    return int(n)


def price(value):
    n = decimal(value)
    if n <= 0 or n.as_tuple().exponent < -2:
        frappe.throw("Positive price with at most two decimals required")
    return n


def product(identifier, company):
    name = frappe.db.get_value(
        "Item", {"ccm_id": identifier, "ccm_company": company}, "name"
    )
    if not name:
        frappe.throw("Product not found", frappe.DoesNotExistError)
    return frappe.get_doc("Item", name)


def stock(item, warehouse):
    value = frappe.db.get_value(
        "Bin",
        {"item_code": item, "warehouse": warehouse},
        ["actual_qty", "valuation_rate", "stock_value"],
        as_dict=True,
    )
    return value or frappe._dict(actual_qty=0, valuation_rate=0, stock_value=0)


def normalized(order):
    return {
        "id": order.external_id,
        "company_id": order.company,
        "status": order.status,
        "channel": order.channel,
        "currency": order.currency,
        **{
            k: order.get(k)
            for k in [
                "gross",
                "revenue",
                "tax",
                "commission",
                "cost",
                "net",
                "indicator",
                "accounting_profit",
                "financed_amount",
                "shipping_expense",
            ]
        },
        "lines": [
            {
                "product_id": frappe.db.get_value("Item", row.product, "ccm_id"),
                "qty": str(quantity(row.qty)),
                "unit_price": row.unit_price,
                "line_total": row.line_total,
                "unit_cost": row.unit_cost,
            }
            for row in order.lines
        ],
    }


def create_order(payload):
    company = payload["company_id"]
    channel = payload.get("channel")
    if channel not in ["STORE", "WEB"]:
        frappe.throw("Invalid channel")
    if payload.get("currency", "USD") != "USD":
        frappe.throw("This shared order fixture is USD-only")
    warehouse = payload["warehouse"]
    if frappe.db.get_value("Warehouse", warehouse, "company") != company:
        frappe.throw("Warehouse company mismatch", frappe.PermissionError)
    customer = frappe.db.get_value(
        "Customer", {"ccm_id": payload["customer_id"], "ccm_company": company}, "name"
    )
    if not customer:
        frappe.throw("Customer outside authorized company", frappe.PermissionError)
    rate = decimal(payload.get("tax_rate", "0"))
    if rate not in [Decimal("0"), Decimal(".10")]:
        frappe.throw("Unknown LAB tax")
    lines = []
    gross = Decimal("0")
    revenue = Decimal("0")
    cost = Decimal("0")
    for row in payload.get("lines", []):
        item = product(row["product_id"], company)
        if not item.cashea_enabled:
            frappe.throw("Product not enabled for Cashea")
        qty = quantity(row["qty"])
        unit = price(row["unit_price"])
        native = stock(item.name, warehouse)
        unit_cost = decimal(native.valuation_rate)
        if unit_cost < 0:
            frappe.throw("Negative ERP product cost")
        total = decimal(money(unit * qty))
        base = decimal(money(total / (1 + rate)))
        gross += total
        revenue += base
        cost += unit_cost * qty
        lines.append(
            {
                "product": item.name,
                "qty": str(qty),
                "unit_price": money(unit),
                "unit_cost": money(unit_cost),
                "line_total": money(total),
            }
        )
    if not lines:
        frappe.throw("At least one line required")
    financed = decimal(payload["financed_amount"])
    if financed < 0 or financed > gross:
        frappe.throw("Invalid financed amount")
    shipping = decimal(payload.get("shipping_expense", "0"))
    if shipping < 0 or (channel == "STORE" and shipping != 0):
        frappe.throw("Invalid merchant shipping expense")
    commission = decimal(
        money(gross * (Decimal(".04") if channel == "STORE" else Decimal(".06")))
    ) + decimal(money(financed * Decimal(".04")))
    net = gross - commission - shipping
    stamp = (
        datetime.fromisoformat(payload["datetime"])
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )
    doc = insert(
        {
            "doctype": "CCM Cashea Order",
            "external_id": payload["id"],
            "company": company,
            "customer": customer,
            "warehouse": warehouse,
            "channel": channel,
            "currency": "USD",
            "order_datetime": stamp,
            "status": "NEW",
            "guide": payload.get("guide"),
            "tax_rate": str(rate),
            "financed_amount": money(financed),
            "shipping_expense": money(shipping),
            "lines": lines,
            "gross": money(gross),
            "revenue": money(revenue),
            "tax": money(gross - revenue),
            "commission": money(commission),
            "cost": money(cost),
            "net": money(net),
            "indicator": money(net - cost),
            "accounting_profit": money(revenue - cost - commission - shipping),
        }
    )
    audit(company, "cashea.created", doc, before={"exists": False},
          after=normalized(doc), reason="LAB order captured without acceptance")
    return normalized(doc)


def taxes(order):
    if not decimal(order.tax_rate):
        return []
    return [
        {
            "charge_type": "On Net Total",
            "account_head": account(order.company, "tax"),
            "description": "TAX-LAB-10 synthetic inclusive",
            "rate": 10,
            "included_in_print_rate": 1,
        }
    ]


def native_sale(order):
    doc = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "company": order.company,
            "customer": order.customer,
            "transaction_date": "2026-10-01",
            "delivery_date": "2026-10-01",
            "currency": "USD",
            "conversion_rate": 1,
            "selling_price_list": "Standard Selling",
            "price_list_currency": "USD",
            "plc_conversion_rate": 1,
            "taxes": taxes(order),
            "items": [
                {
                    "item_code": r.product,
                    "qty": quantity(r.qty),
                    "rate": float(decimal(r.unit_price)),
                    "warehouse": order.warehouse,
                    "delivery_date": "2026-10-01",
                }
                for r in order.lines
            ],
        }
    )
    return post(doc)


def fulfill(order):
    if order.channel == "WEB" and not order.guide:
        frappe.throw("WEB dispatch requires guide")
    for row in order.lines:
        if decimal(stock(row.product, order.warehouse).actual_qty) < quantity(row.qty):
            frappe.throw("Insufficient physical stock")
    from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
    from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

    note = make_delivery_note(order.sale_order)
    note.set_posting_time = 1
    note.posting_date = "2026-10-01"
    note.posting_time = "10:00:00"
    note = post(note)
    invoice = make_sales_invoice(note.name)
    invoice.set_posting_time = 1
    invoice.posting_date = "2026-10-01"
    invoice.posting_time = "10:01:00"
    invoice.update_stock = 0
    invoice.disable_rounded_total = 1
    invoice.po_no = "INV-CCM-001" if order.external_id == "CO00" else order.external_id
    for row in invoice.items:
        row.income_account = account(order.company, "income")
        row.expense_account = account(order.company, "cogs")
        row.cost_center = frappe.db.get_value("Company", order.company, "cost_center")
    invoice = post(invoice)
    if (
        money(invoice.grand_total) != order.gross
        or money(invoice.total_taxes_and_charges) != order.tax
    ):
        frappe.throw("Native invoice differs from frozen oracle")
    entries = frappe.get_all(
        "Stock Ledger Entry",
        filters={
            "voucher_type": "Delivery Note",
            "voucher_no": note.name,
            "is_cancelled": 0,
        },
        fields=["stock_value_difference"],
    )
    actual_cost = -sum(decimal(r.stock_value_difference) for r in entries)
    order.cost = money(actual_cost)
    order.indicator = money(decimal(order.net) - actual_cost)
    order.accounting_profit = money(
        decimal(order.revenue)
        - actual_cost
        - decimal(order.commission)
        - decimal(order.shipping_expense)
    )
    order.delivery_note = note.name
    order.sales_invoice = invoice.name


def settle(order):
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    invoice = frappe.get_doc("Sales Invoice", order.sales_invoice)
    upfront = decimal(order.gross) - decimal(order.financed_amount)
    payments = []
    if upfront:
        pay = get_payment_entry(
            "Sales Invoice",
            invoice.name,
            party_amount=float(upfront),
            bank_account=account(order.company, "cash"),
        )
        pay.posting_date = "2026-10-01"
        payments.append(post(pay).name)
    fee = decimal(order.commission)
    ship = decimal(order.shipping_expense)
    financed = decimal(order.financed_amount)
    pay = get_payment_entry(
        "Sales Invoice",
        invoice.name,
        party_amount=float(financed),
        bank_account=account(order.company, "bank"),
    )
    pay.posting_date = "2026-10-01"
    pay.reference_no = "CASHEA-" + order.external_id
    pay.reference_date = "2026-10-01"
    pay.paid_amount = float(financed - fee - ship)
    pay.received_amount = float(financed - fee - ship)
    pay.append(
        "deductions",
        {
            "account": account(order.company, "commission"),
            "cost_center": frappe.db.get_value("Company", order.company, "cost_center"),
            "amount": float(fee),
        },
    )
    if ship:
        pay.append(
            "deductions",
            {
                "account": account(order.company, "shipping"),
                "cost_center": frappe.db.get_value(
                    "Company", order.company, "cost_center"
                ),
                "amount": float(ship),
            },
        )
    payments.append(post(pay).name)
    order.payments = json.dumps(payments)


def transition_order(payload):
    name = frappe.db.get_value(
        "CCM Cashea Order",
        {"external_id": payload["id"], "company": payload["company_id"]},
        "name",
    )
    if not name:
        frappe.throw("Order not found")
    with frappe.cache.lock("ccm-order:" + name, timeout=300, blocking_timeout=110):
        frappe.db.commit()
        doc = frappe.get_doc("CCM Cashea Order", name)
        target = payload["target"]
        before = normalized(doc)
        actor_roles = (
            ["CCM Operator"]
            if target in ["FULFILLED", "SHIPPED", "PREPARING"]
            else ["CCM Simulator"]
        )
        access(doc.company, actor_roles)
        paths = {
            "NEW": ["REVIEWED", "REJECTED", "CANCELLED"],
            "REVIEWED": ["APPROVED", "REJECTED", "CANCELLED"],
            "APPROVED": ["PREPARING", "CANCELLED"]
            if doc.channel == "WEB"
            else ["FULFILLED", "CANCELLED"],
            "PREPARING": ["SHIPPED", "CANCELLED"],
            "FULFILLED": ["SETTLED"],
            "SHIPPED": ["SETTLED"],
        }
        if target not in paths.get(doc.status, []):
            frappe.throw("Invalid state transition", frappe.TimestampMismatchError)
        if target == "APPROVED":
            doc.sale_order = native_sale(doc).name
        if target in ["SHIPPED", "FULFILLED"]:
            fulfill(doc)
        if target == "SETTLED":
            settle(doc)
        if target == "CANCELLED" and doc.sale_order:
            native = frappe.get_doc("Sales Order", doc.sale_order)
            native.flags.ignore_permissions = True
            native.cancel()
        doc.status = target
        save(doc)
        reason = payload.get("reason") or {
            "REVIEWED": "LAB technical validation",
            "APPROVED": "LAB acceptance by authenticated Cashea simulator",
            "PREPARING": "LAB web order preparation",
            "FULFILLED": "LAB direct handover in store",
            "SHIPPED": "LAB carrier handover with guide",
            "SETTLED": "LAB settlement by authenticated Cashea simulator",
            "REJECTED": "LAB rejection before physical handover",
            "CANCELLED": "LAB cancellation before physical handover",
        }[target]
        audit(doc.company, "cashea." + target.lower(), doc, before,
              normalized(doc), reason=reason)
        if target == "APPROVED":
            event(doc.company, "cashea.approved", doc)
        return normalized(doc)
