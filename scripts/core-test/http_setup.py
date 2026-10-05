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
        },
        indent=2,
    )
    + "\n"
)
print("Prepared independent HTTP snapshots and native serial-search fixture.")
