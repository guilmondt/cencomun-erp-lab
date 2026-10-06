"""Native fixture setup for the isolated Core Test site. No business SQL."""

import json, secrets
from pathlib import Path
import frappe
from frappe.core.doctype.user.user import generate_keys
from cencomun_erp.core.guards import service

ROOT = Path("/workspace/.local/frappe-integral")
REPO = Path("/workspace/cencomun-erp-lab")
COMPANY = "CCM-LAB-001"
ABBR = "CLAB"
private_path = ROOT / (
    "core-private.json"
    if frappe.local.site == "ccm-core.test"
    else "core-private-" + frappe.local.site + ".json"
)
private = (
    json.loads(private_path.read_text())
    if private_path.exists()
    else {
        "admin_password": json.loads((ROOT / "core-private.json").read_text())[
            "admin_password"
        ]
    }
)
frappe.set_user("Administrator")
from erpnext.setup.setup_wizard.operations.install_fixtures import install

install("United States")
if not frappe.db.exists("Currency", "VES"):
    frappe.get_doc(
        {
            "doctype": "Currency",
            "currency_name": "VES",
            "fraction": "Centimo",
            "fraction_units": 100,
            "smallest_currency_fraction_value": 0.01,
            "symbol": "Bs",
            "enabled": 1,
        }
    ).insert()
if not frappe.db.exists("Fiscal Year", "2026"):
    frappe.get_doc(
        {
            "doctype": "Fiscal Year",
            "year": "2026",
            "year_start_date": "2026-01-01",
            "year_end_date": "2026-12-31",
        }
    ).insert()
frappe.conf.ccm_lab_enabled = 1
from frappe.installer import update_site_config

update_site_config("ccm_lab_enabled", 1)
update_site_config("ccm_company", COMPANY)
if not frappe.db.exists("Company", COMPANY):
    frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": COMPANY,
            "abbr": ABBR,
            "country": "United States",
            "default_currency": "USD",
            "create_chart_of_accounts_based_on": "Standard Template",
            "chart_of_accounts": "Standard",
            "enable_perpetual_inventory": 1,
        }
    ).insert()
for label, kind in [("Standard Selling", "selling"), ("Standard Buying", "buying")]:
    if not frappe.db.exists("Price List", label):
        frappe.get_doc(
            {
                "doctype": "Price List",
                "price_list_name": label,
                "currency": "USD",
                "enabled": 1,
                kind: 1,
            }
        ).insert()
company = frappe.get_doc("Company", COMPANY)
for field, label in {
    "default_income_account": "Sales",
    "default_expense_account": "Cost of Goods Sold",
    "default_inventory_account": "Stock In Hand",
    "stock_adjustment_account": "Stock Adjustment",
    "default_cash_account": "Cash",
    "round_off_account": "Round Off",
    "exchange_gain_loss_account": "Exchange Gain/Loss",
    "stock_received_but_not_billed": "Stock Received But Not Billed",
    "default_payable_account": "Creditors",
}.items():
    setattr(company, field, label + " - " + ABBR)
company.save()
accounts = {
    "income": company.default_income_account,
    "cogs": company.default_expense_account,
    "receivable": company.default_receivable_account,
    "stock": company.default_inventory_account,
    "cash": f"Cash - {ABBR}",
}


def new_account(label, parent, account_type=None, currency="USD"):
    name = f"{label} - {ABBR}"
    if not frappe.db.exists("Account", name):
        frappe.get_doc(
            {
                "doctype": "Account",
                "account_name": label,
                "parent_account": f"{parent} - {ABBR}",
                "company": COMPANY,
                "account_type": account_type,
                "account_currency": currency,
                "is_group": 0,
            }
        ).insert()
    return name


accounts["bank"] = new_account("CCM Bank", "Bank Accounts", "Bank")
accounts["commission"] = new_account(
    "CCM Commission", "Indirect Expenses", "Expense Account"
)
accounts["shipping"] = new_account(
    "CCM Delivery", "Indirect Expenses", "Expense Account"
)
accounts["tax"] = new_account("CCM Synthetic Tax", "Duties and Taxes", "Tax")
accounts["cash_ves"] = new_account("CCM VES Cash", "Cash In Hand", "Cash", "VES")
accounts["pos"] = new_account("CCM POS Captured", "Current Assets")
accounts["transfer"] = new_account("CCM Transfers", "Bank Accounts", "Bank")
accounts["opening"] = company.default_expense_account
update_site_config("ccm_accounts", accounts)
frappe.conf.ccm_accounts = accounts
if not frappe.db.exists("Bank", "CCM Fictional Bank"):
    frappe.get_doc({"doctype": "Bank", "bank_name": "CCM Fictional Bank"}).insert()
if not frappe.db.exists("Bank Account", {"account": accounts["bank"]}):
    bank_account = (
        frappe.get_doc(
            {
                "doctype": "Bank Account",
                "account_name": "CCM LAB Bank",
                "bank": "CCM Fictional Bank",
                "account": accounts["bank"],
                "is_company_account": 1,
                "company": COMPANY,
            }
        )
        .insert()
        .name
    )
else:
    bank_account = frappe.db.get_value(
        "Bank Account", {"account": accounts["bank"]}, "name"
    )
update_site_config("ccm_bank_account", bank_account)
frappe.conf.ccm_bank_account = bank_account
for dt, label, parentfield, parent in [
    (
        "Customer Group",
        "CCM LAB Customers",
        "parent_customer_group",
        "All Customer Groups",
    ),
    (
        "Supplier Group",
        "CCM LAB Suppliers",
        "parent_supplier_group",
        "All Supplier Groups",
    ),
    ("Item Group", "CCM LAB Products", "parent_item_group", "All Item Groups"),
]:
    namefield = dt.lower().replace(" ", "_") + "_name"
    if not frappe.db.exists(dt, label):
        frappe.get_doc(
            {"doctype": dt, namefield: label, parentfield: parent, "is_group": 0}
        ).insert()
for data in json.loads((REPO / "fixtures/ccm-core-v1/customers.json").read_text()):
    if not frappe.db.exists("Customer", {"ccm_id": data["id"]}):
        frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": data["name"],
                "customer_type": "Individual",
                "customer_group": "CCM LAB Customers",
                "territory": "All Territories",
                "ccm_id": data["id"],
                "ccm_company": COMPANY,
            }
        ).insert()
for data in json.loads((REPO / "fixtures/ccm-core-v1/customers.json").read_text()):
    customer = frappe.get_doc(
        "Customer", frappe.db.get_value("Customer", {"ccm_id": data["id"]}, "name")
    )
    customer.ccm_company = COMPANY
    if not customer.customer_primary_contact:
        contact = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": "Fictitious " + data["id"],
                "email_ids": [{"email_id": data["email"], "is_primary": 1}],
                "phone_nos": [
                    {
                        "phone": data["phone"],
                        "is_primary_phone": 1,
                        "is_primary_mobile_no": 1,
                    }
                ],
                "links": [{"link_doctype": "Customer", "link_name": customer.name}],
            }
        ).insert()
        customer.customer_primary_contact = contact.name
    customer.save()
if not frappe.db.exists("Supplier", "SUP-LAB"):
    frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": "SUP-LAB",
            "supplier_group": "CCM LAB Suppliers",
            "supplier_type": "Company",
        }
    ).insert()
for data in json.loads((REPO / "fixtures/ccm-core-v1/products.json").read_text()):
    if not frappe.db.exists("Item", data["id"]):
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": data["id"],
                "item_name": data["name"],
                "item_group": "CCM LAB Products",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "valuation_method": "Moving Average",
                "ccm_company": COMPANY,
                "ccm_id": data["id"],
                "marketplace_enabled": int(data["marketplace_enabled"]),
                "cashea_enabled": int(data["cashea_enabled"]),
                "cashea_price": data["price"],
                "supplier_reference": data["supplier_reference"],
                "warranty_quantity": data["warranty_quantity"],
                "warranty_unit": data["warranty_unit"],
                "ccm_condition": data["condition"],
            }
        ).insert()
roles = {
    "reader": ["CCM Reader"],
    "operator": ["CCM Operator"],
    "buyer": ["CCM Buyer"],
    "manager": ["CCM Manager"],
    "director": ["CCM Director"],
    "simulator": ["CCM Simulator"],
    "mcp": ["CCM MCP"],
    "selfbuyer": ["CCM Operator", "CCM Buyer"],
    "other": ["CCM Reader"],
}
private.setdefault("users", {})
for label, user_roles in roles.items():
    email = label + "@example.invalid"
    if not frappe.db.exists("User", email):
        password = secrets.token_urlsafe(32)
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Synthetic " + label,
                "send_welcome_email": 0,
                "new_password": password,
                "enabled": 1,
                "user_type": "System User",
                "roles": [{"role": r} for r in user_roles],
            }
        ).insert()
    if label not in private["users"] or private["users"][label].get(
        "api_key"
    ) != frappe.db.get_value("User", email, "api_key"):
        keys = generate_keys(email)
        user = frappe.get_doc("User", email)
        private["users"][label] = {
            "email": email,
            "api_key": user.api_key,
            "api_secret": keys["api_secret"],
        }
    if label != "other" and not frappe.db.exists(
        "User Permission", {"user": email, "allow": "Company", "for_value": COMPANY}
    ):
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": email,
                "allow": "Company",
                "for_value": COMPANY,
                "apply_to_all_doctypes": 1,
            }
        ).insert()
for day, rate in json.loads((REPO / "fixtures/ccm-core-v1/profile.json").read_text())[
    "rates"
].items():
    if not frappe.db.exists(
        "Currency Exchange", {"date": day, "from_currency": "USD", "to_currency": "VES"}
    ):
        frappe.get_doc(
            {
                "doctype": "Currency Exchange",
                "date": day,
                "from_currency": "USD",
                "to_currency": "VES",
                "exchange_rate": float(rate),
                "for_buying": 1,
                "for_selling": 1,
            }
        ).insert()
private_path.write_text(json.dumps(private))
private_path.chmod(0o600)
frappe.db.commit()
print(
    "Seeded company, native accounts, products, customers and 9 restricted synthetic actors."
)
print("Company native defaults:", {k: bool(v) for k, v in accounts.items()})
