"""Non-secret native error-tail diagnostics for the isolated site."""

import frappe

for row in frappe.get_all(
    "Error Log",
    filters={"method": ["like", "CCM LAB%"]},
    fields=["method", "error"],
    order_by="creation desc",
    limit=4,
):
    print(row.method)
    print("\n".join(row.error.splitlines()[-16:]))
