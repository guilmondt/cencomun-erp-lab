"""Supported document and list permission hooks: absence of scope means denial."""

import frappe

FIELD = {"Item": "ccm_company", "Customer": "ccm_company"}


def companies(user):
    return frappe.get_all(
        "User Permission", filters={"user": user, "allow": "Company"}, pluck="for_value"
    )


def document(doc, ptype=None, user=None, **kwargs):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    if not frappe.conf.get("ccm_lab_enabled"):
        return True
    field = FIELD.get(doc.doctype, "company")
    company = doc.get(field)
    if doc.doctype == "Bin":
        company = frappe.db.get_value("Warehouse", doc.warehouse, "company")
    if doc.doctype == "Contact":
        company = next(
            (
                frappe.db.get_value("Customer", row.link_name, "ccm_company")
                for row in doc.links
                if row.link_doctype == "Customer"
            ),
            None,
        )
    if frappe.flags.ccm_service:
        return True  # Scoped, checked internal native factory.
    return bool(company and company in companies(user))


def condition(doctype, user=None):
    user = user or frappe.session.user
    if user == "Administrator" or not frappe.conf.get("ccm_lab_enabled"):
        return ""
    allowed = companies(user)
    if not allowed:
        return "1=0"
    field = FIELD.get(doctype, "company")
    if doctype == "Bin":
        names = frappe.get_all(
            "Warehouse", filters={"company": ["in", allowed]}, pluck="name"
        )
        field = "warehouse"
    elif doctype == "Contact":
        customers = frappe.get_all(
            "Customer", filters={"ccm_company": ["in", allowed]}, pluck="name"
        )
        names = (
            frappe.get_all(
                "Dynamic Link",
                filters={
                    "parenttype": "Contact",
                    "link_doctype": "Customer",
                    "link_name": ["in", customers],
                },
                pluck="parent",
            )
            if customers
            else []
        )
        field = "name"
    else:
        names = allowed
    if not names:
        return "1=0"
    return (
        "`tab"
        + doctype
        + "`.`"
        + field
        + "` in ("
        + ",".join(frappe.db.escape(x) for x in names)
        + ")"
    )


# Hook callables have fixed table names; clients cannot supply SQL identifiers.
DTYPES = [
    "Bin",
    "Contact",
    "Item",
    "Customer",
    "Account",
    "Warehouse",
    "Sales Order",
    "Sales Invoice",
    "Delivery Note",
    "Purchase Order",
    "GL Entry",
    "Payment Entry",
    "Journal Entry",
    "Bank Transaction",
    "Stock Entry",
    "Serial No",
    "CCM Cashea Order",
    "CCM Cash Closing",
    "CCM Purchase Request",
    "CCM Audit",
    "CCM Event",
    "CCM Request Key",
    "CCM Import",
    "CCM Bank Match",
    "CCM Rate Authorization",
]
for _dt in DTYPES:

    def _query(user=None, _doctype=_dt):
        return condition(_doctype, user)

    globals()["query_" + _dt.lower().replace(" ", "_")] = _query


def after_request(request=None, response=None):
    """Persist native API denials after Frappe has rolled back its transaction."""
    if (
        not frappe.conf.get("ccm_lab_enabled")
        or not response
        or response.status_code not in [403, 417]
    ):
        return
    if frappe.session.user == "Guest":
        return
    import uuid
    from cencomun_erp.core.business import audit

    audit(
        frappe.conf.ccm_company,
        "request.native.denied"
        if response.status_code == 403
        else "request.native.rejected",
        obj=frappe._dict(doctype="Native Request", name=request.path),
        before={"state": "attempted"},
        after={"status": response.status_code, "state": "rejected"},
        reason="Native server validation/permission",
        correlation=str(uuid.uuid4()),
    )
    frappe.db.commit()
