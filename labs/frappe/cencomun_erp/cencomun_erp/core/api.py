"""Authenticated LAB boundary. Six neutral operations plus test/admin actions.

All native writes go through scoped services; the external adapter never opens DB.
"""

import json, time, uuid, functools
import frappe
from cencomun_erp.core import business as b, finance as f
from cencomun_erp.core.guards import decimal, money

WRITES = {
    "createCasheaOrder": (["CCM Operator", "CCM MCP"], b.create_order),
    "createPurchaseDraft": (["CCM Operator", "CCM MCP"], f.create_purchase),
    "transitionOrder": (["CCM Operator", "CCM Simulator"], b.transition_order),
    "purchaseAction": (
        ["CCM Operator", "CCM Buyer", "CCM Manager", "CCM Director"],
        f.purchase_action,
    ),
    "createClosing": (["CCM Operator"], f.create_closing),
    "confirmClosing": (["CCM Manager"], f.confirm_closing),
    "importBank": (["CCM Operator"], f.import_bank),
    "reconcileBank": (["CCM Manager"], f.reconcile_bank),
    "authorizeRate": (["CCM Manager"], f.authorize_rate),
    "currencyPayment": (["CCM Operator"], f.currency_payment),
}


def reads(operation, p):
    company = p["company_id"]
    b.access(company, b.READERS)
    if operation == "searchProducts":
        q = str(p.get("q", "")).casefold()
        page = int(p.get("page", 1))
        size = int(p.get("page_size", 20))
        if page < 1 or size < 1 or size > 1000:
            frappe.throw("Invalid pagination")
        fields = [
            "name",
            "ccm_id",
            "item_name",
            "supplier_reference",
            "marketplace_enabled",
            "cashea_enabled",
            "cashea_price",
            "warranty_quantity",
            "warranty_unit",
            "ccm_condition",
        ]
        rows = frappe.get_all(
            "Item",
            filters={"ccm_company": company, "disabled": 0},
            fields=fields,
            order_by="ccm_id asc",
        )
        items = [
            {
                "id": r.ccm_id,
                "name": r.item_name,
                "supplier_reference": r.supplier_reference,
                "marketplace_enabled": bool(r.marketplace_enabled),
                "cashea_enabled": bool(r.cashea_enabled),
                "price": money(r.cashea_price),
                "warranty_quantity": r.warranty_quantity,
                "warranty_unit": r.warranty_unit,
                "condition": r.ccm_condition,
            }
            for r in rows
            if any(
                q in str(r.get(k) or "").casefold()
                for k in ["ccm_id", "item_name", "supplier_reference"]
            )
        ]
        return {
            "items": items[(page - 1) * size : page * size],
            "total": len(items),
            "page": page,
            "page_size": size,
        }
    if operation == "getInventory":
        item = b.product(p["product_id"], company)
        wh = p["warehouse"]
        if frappe.db.get_value("Warehouse", wh, "company") != company:
            frappe.throw("Warehouse denied", frappe.PermissionError)
        s = b.stock(item.name, wh)
        return {
            "product_id": item.ccm_id,
            "warehouse": wh,
            "unit": item.stock_uom,
            "on_hand": str(int(s.actual_qty)),
            "reserved": "0",
            "available": str(int(s.actual_qty)),
            "value": money(s.stock_value),
            "unit_cost": money(s.valuation_rate),
        }
    if operation == "getCustomerBalance":
        customer = frappe.db.get_value(
            "Customer", {"ccm_id": p["customer_id"], "ccm_company": company}, "name"
        )
        if not customer:
            frappe.throw("Customer not found")
        invoices = frappe.get_all(
            "Sales Invoice",
            filters={"company": company, "customer": customer, "docstatus": 1},
            fields=["currency", "outstanding_amount"],
        )
        sums = {}
        for row in invoices:
            sums[row.currency] = sums.get(row.currency, decimal(0)) + decimal(
                row.outstanding_amount
            )
        return {
            "customer_id": p["customer_id"],
            "balances": {k: money(v) for k, v in sorted(sums.items())}
            or {"USD": "0.00"},
        }
    if operation == "getCashStatus":
        filters = {"company": company}
        if p.get("id"):
            filters["external_id"] = p["id"]
        name = frappe.db.get_value(
            "CCM Cash Closing", filters, "name", order_by="creation desc"
        )
        if not name:
            return {
                "state": "EMPTY",
                "channels": [],
                "cashea_pending": "0.00",
                "cashea_received": "0.00",
            }
        doc = frappe.get_doc("CCM Cash Closing", name)
        return {"id": doc.external_id, "state": doc.state, **json.loads(doc.snapshot)}
    frappe.throw("Unknown operation")


def measured(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not frappe.conf.get("ccm_measure_queries"):
            return fn(*args, **kwargs)
        from frappe.recorder import record

        recorder = record(force=True)
        try:
            result = fn(*args, **kwargs)
            result["query_count"] = len(recorder.calls)
            result["db_ms"] = round(sum(row["duration"] for row in recorder.calls), 4)
            return result
        finally:
            recorder._unpatch_sql()
            if hasattr(frappe.local, "_recorder"):
                delattr(frappe.local, "_recorder")

    return wrapper


@frappe.whitelist()
@measured
def execute(operation, payload=None, key=None):
    started = time.perf_counter()
    p = json.loads(payload) if isinstance(payload, str) else (payload or {})
    correlation = str(uuid.uuid4())
    frappe.local.ccm_correlation = correlation
    try:
        if operation in WRITES:
            roles, fn = WRITES[operation]
            result = b.write(operation, key, p, roles, lambda: fn(p))
            status = (
                200
                if result.get("replay")
                else 201
                if operation
                in ["createCasheaOrder", "createPurchaseDraft", "createClosing"]
                else 200
            )
        else:
            result = reads(operation, p)
            status = 200
        return {
            "ok": True,
            "status": status,
            "result": result,
            "correlation_id": correlation,
            "server_ms": round((time.perf_counter() - started) * 1000, 4),
        }
    except Exception as exc:
        frappe.db.rollback()
        code = (
            403
            if isinstance(exc, frappe.PermissionError)
            else 409
            if isinstance(
                exc,
                (
                    frappe.TimestampMismatchError,
                    frappe.DuplicateEntryError,
                    frappe.UniqueValidationError,
                ),
            )
            else 422
            if isinstance(
                exc, (frappe.ValidationError, ValueError, KeyError, TypeError)
            )
            else 500
        )
        # Permission failures are committed separately, never accompanied by success events.
        company = p.get("company_id")
        if company == frappe.conf.get("ccm_company") and frappe.session.user != "Guest":
            b.audit(
                company,
                "request.denied" if code == 403 else "request.rejected",
                obj=frappe._dict(doctype="API Command", name=p.get("id") or operation),
                before={"state": "attempted"},
                after={"operation": operation, "code": code, "state": "rejected"},
                reason=type(exc).__name__,
                correlation=correlation,
            )
            frappe.db.commit()
        # Diagnostic traceback stays in the site's private error log, not the response.
        if code == 500:
            frappe.log_error(title="CCM LAB " + operation)
        return {
            "ok": False,
            "status": code,
            "error": {
                "code": str(code),
                "message": str(exc).split("\n")[0]
                if code != 500
                else "Internal LAB error; consult private site log",
                "correlation_id": correlation,
            },
            "server_ms": round((time.perf_counter() - started) * 1000, 4),
        }
