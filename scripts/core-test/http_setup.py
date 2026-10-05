"""Independent native snapshots for concurrent HTTP/idempotency/recovery tests."""

import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from support import *

wh = warehouse("HTTP")
conc = warehouse("TAX-CONC-S")
web = warehouse("TAX-CONC-W")
lost = warehouse("LOST")
orders = json.loads((REPO / "fixtures/ccm-core-v1/orders.json").read_text())
for src, identifier, warehouse_name in [
    (orders[2], "TAX-CONC-S", conc),
    (orders[3], "TAX-CONC-W", web),
]:
    p = payload({**src, "id": identifier}, warehouse_name)
    call("createCasheaOrder", p)
    for target in ["REVIEWED", "APPROVED"]:
        call(
            "transitionOrder",
            payload({"id": identifier, "target": target}),
            "simulator",
            identifier + ":" + target,
        )
    if p["channel"] == "WEB":
        call(
            "transitionOrder",
            payload({"id": identifier, "target": "PREPARING"}),
            "operator",
            identifier + ":PREPARING",
        )
mcp_orders = {}
for identifier, source, physical in [
    ("MCP-DENY-DELIVER-S", orders[0], False),
    ("MCP-DENY-DELIVER-W", orders[1], False),
    ("MCP-DENY-SETTLE-S", orders[0], True),
    ("MCP-DENY-SETTLE-W", orders[1], True),
]:
    case_wh = warehouse(identifier)
    call("createCasheaOrder", payload({**source, "id": identifier}, case_wh))
    path = ["REVIEWED", "APPROVED"]
    if source["channel"] == "WEB":
        path.append("PREPARING")
    if physical:
        path.append("SHIPPED" if source["channel"] == "WEB" else "FULFILLED")
    for target in path:
        call("transitionOrder", payload({"id": identifier, "target": target}),
             "operator" if target in ["PREPARING", "FULFILLED", "SHIPPED"] else "simulator",
             identifier + ":" + target)
    mcp_orders[identifier] = order_effects(identifier)

call("createClosing", payload({"id": "MCP-DENY-CS", "channels": []}),
     "operator", "MCP-DENY-CS:create")
bank = call("importBank", payload({"id": "MCP-DENY-BANK", "account_id": "BANK-USD-001",
    "csv": "account,date,reference,currency,amount,description\nBANK-USD-001,2026-10-01,MCP-DENY-BANK,USD,40.00,Synthetic MCP permission target\n"}),
    "operator", "MCP-DENY-BANK:import")
row = bank["results"][0]
expect(row["classification"], "AMBIGUOUS")
payment = next(name for name in row["candidates"]
               if frappe.db.get_value("Payment Entry", name, "reference_no") == "AMB-BOOK-B")
expect(frappe.db.exists("Currency Exchange", {
    "date": "2026-10-04", "from_currency": "USD", "to_currency": "VES"}), None)
frappe.set_user("Administrator")
if not frappe.db.exists("Serial No", "SER-P001-001"):
    frappe.get_doc(
        {
            "doctype": "Serial No",
            "serial_no": "SER-P001-001",
            "item_code": "P001",
            "company": COMPANY,
        }
    ).insert()
frappe.db.commit()
(OUT / "http-mapping.json").write_text(
    json.dumps(
        {
            "company_id": COMPANY,
            "warehouse": wh,
            "lost_warehouse": lost,
            "concurrent": {"TAX-CONC-S": conc, "TAX-CONC-W": web},
            "invoice": order_doc("CO00").sales_invoice,
            "mcp_denial_baseline": {
                "orders": mcp_orders,
                "closing": {"id": "MCP-DENY-CS", "state": "DRAFT"},
                "rate": {"id": "MCP-DENY-FX", "date": "2026-10-04", "rate": None},
                "bank": {"key": row["key"], "payment": payment, "reconciled": False,
                         "unallocated_amount": "40.00", "native_transaction": row["native_transaction"]},
            },
        },
        indent=2,
    )
    + "\n"
)
print("Prepared independent HTTP snapshots and native serial-search fixture.")
