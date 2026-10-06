"""Registration and supported hooks for the approved LAB-only Core Test."""

app_name = "cencomun_erp"
app_title = "Cencomun ERP"
app_publisher = "Cencomun"
app_description = "Cencomun ERP evaluation app skeleton for Frappe 16"
app_email = "maintainers@example.invalid"  # Placeholder, not a real contact.
app_license = "UNLICENSED"  # No license grant has been selected by the owner.

required_apps = ["erpnext"]

after_install = "cencomun_erp.core.setup.install"
after_migrate = "cencomun_erp.core.setup.install"
doc_events = {"Item": {"validate": "cencomun_erp.core.guards.validate_item"}}

for _native in [
    "Sales Order",
    "Delivery Note",
    "Sales Invoice",
    "Payment Entry",
    "Purchase Order",
    "Journal Entry",
    "Bank Transaction",
    "Stock Entry",
]:
    doc_events[_native] = {
        event: "cencomun_erp.core.guards.native_write_guard"
        for event in ["validate", "before_submit", "before_cancel", "on_trash"]
    }

_scoped_doctypes = [
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
has_permission = {
    dt: "cencomun_erp.core.permissions.document" for dt in _scoped_doctypes
}
permission_query_conditions = {
    dt: "cencomun_erp.core.permissions.query_" + dt.lower().replace(" ", "_")
    for dt in _scoped_doctypes
}

after_request = ["cencomun_erp.core.permissions.after_request"]
