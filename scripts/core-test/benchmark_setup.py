"""Native loading of the frozen, isolated performance profile."""

import json, sys
from pathlib import Path
import frappe
from frappe.installer import update_site_config
from frappe.recorder import RecorderConfig
from cencomun_erp.core import business as b

REPO = Path("/workspace/cencomun-erp-lab")
sys.path.insert(0, str(REPO / "scripts/core-test"))
from support import COMPANY, ABBR, OUT, expect

spec = json.loads((REPO / "fixtures/ccm-core-v1/benchmark.json").read_text())
frappe.set_user("Administrator")
wh = "WH-LAB-001-BENCH - " + ABBR
if not frappe.db.exists("Warehouse", wh):
    frappe.get_doc(
        {
            "doctype": "Warehouse",
            "warehouse_name": "WH-LAB-001-BENCH",
            "company": COMPANY,
            "parent_warehouse": "All Warehouses - " + ABBR,
        }
    ).insert()
for i, row in enumerate(spec["products"]):
    if not frappe.db.exists("Item", row["id"]):
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": row["id"],
                "item_name": row["name"],
                "item_group": "CCM LAB Products",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "valuation_method": "Moving Average",
                "ccm_company": COMPANY,
                "ccm_id": row["id"],
                "marketplace_enabled": 1,
                "cashea_enabled": 1,
                "cashea_price": row["price"],
                "supplier_reference": row["id"],
                "warranty_quantity": 0,
                "warranty_unit": "DAY",
                "ccm_condition": "NEW",
            }
        ).insert()
    if i % 100 == 0:
        print("Products", i, flush=True)
for row in spec["customers"]:
    if not frappe.db.exists("Customer", {"ccm_id": row["id"]}):
        frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": row["name"],
                "customer_type": "Individual",
                "customer_group": "CCM LAB Customers",
                "territory": "All Territories",
                "ccm_id": row["id"],
                "ccm_company": COMPANY,
            }
        ).insert()
if not frappe.db.exists(
    "Stock Entry", {"remarks": "Core benchmark snapshot", "docstatus": 1}
):
    b.post(
        frappe.get_doc(
            {
                "doctype": "Stock Entry",
                "company": COMPANY,
                "stock_entry_type": "Material Receipt",
                "purpose": "Material Receipt",
                "posting_date": "2026-10-01",
                "posting_time": "08:00:00",
                "set_posting_time": 1,
                "remarks": "Core benchmark snapshot",
                "items": [
                    {
                        "item_code": row["id"],
                        "qty": 5,
                        "t_warehouse": wh,
                        "basic_rate": 1,
                        "expense_account": b.account(COMPANY, "opening"),
                    }
                    for row in spec["products"]
                ],
            }
        )
    )
frappe.db.commit()
for i, row in enumerate(spec["orders"]):
    p = {
        "company_id": COMPANY,
        "id": row["id"],
        "customer_id": row["customer_id"],
        "warehouse": wh,
        "channel": "STORE",
        "currency": "USD",
        "tax_rate": "0",
        "financed_amount": row["financed"],
        "shipping_expense": "0.00",
        "guide": None,
        "datetime": spec["clock"],
        "lines": [
            {
                "product_id": row["product_id"],
                "qty": row["qty"],
                "unit_price": row["price"],
            }
        ],
    }
    frappe.set_user("operator@example.invalid")
    b.write(
        "createCasheaOrder",
        "BENCH-SEED:" + row["id"],
        p,
        ["CCM Operator"],
        lambda p=p: b.create_order(p),
    )
    if i % 100 == 0:
        print("NEW orders", i, flush=True)
frappe.set_user("Administrator")
counts = {
    "products": frappe.db.count("Item", {"ccm_id": ["like", "BENCH-P%"]}),
    "customers": frappe.db.count("Customer", {"ccm_id": ["like", "BENCH-C%"]}),
    "orders": frappe.db.count(
        "CCM Cashea Order", {"external_id": ["like", "BENCH-O%"]}
    ),
    "bank_rows": frappe.db.count(
        "Bank Transaction", {"reference_number": ["like", "BENCH-B%"]}
    ),
}
expect(counts, {"products": 1000, "customers": 100, "orders": 1000, "bank_rows": 1000})
(OUT / "benchmark-loaded.json").write_text(
    json.dumps({"counts": counts, "warehouse": wh, "seed": 100}, indent=2) + "\n"
)
RecorderConfig(
    record_sql=True, capture_stack=False, capture_doc_events=False, explain=False
).store()
update_site_config("ccm_measure_queries", 1)
frappe.conf.ccm_measure_queries = 1
frappe.db.commit()
print("Loaded exact benchmark profile and enabled native query recorder metrics.")
