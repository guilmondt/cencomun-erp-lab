"""Prepare fictitious validation identity through supported Frappe APIs."""

import json
import os
from pathlib import Path

import frappe
import erpnext
import cencomun_erp
from frappe.core.doctype.user.user import generate_keys

ROOT = Path("/workspace/.local/frappe-integral")
private = ROOT / "secrets.json"
credentials = json.loads(private.read_text())
os.chdir(ROOT / "bench/sites")
frappe.init(site="ccm-frappe.test", sites_path=str(ROOT / "bench/sites"))
frappe.connect()
try:
    frappe.set_user("Administrator")
    email = credentials["validation_email"]
    if not frappe.db.exists("User", email):
        frappe.get_doc({
            "doctype": "User", "email": email, "first_name": "Synthetic",
            "last_name": "Validation", "enabled": 1, "user_type": "System User",
            "send_welcome_email": 0, "new_password": credentials["user_password"],
            "roles": [{"role": "System Manager"}],
        }).insert()
    if "api_secret" not in credentials:
        generated = generate_keys(email)
        credentials["api_secret"] = generated["api_secret"]
        credentials["api_key"] = frappe.get_doc("User", email).api_key
        private.write_text(json.dumps(credentials))
        private.chmod(0o600)
    frappe.db.commit()
    installed = frappe.get_installed_apps()
    assert all(app in installed for app in ("frappe", "erpnext", "cencomun_erp")), installed
    assert frappe.get_module_list("cencomun_erp") == ["Cencomun ERP"]
    assert frappe.get_doc("Module Def", "Cencomun ERP").app_name == "cencomun_erp"
    assert frappe.get_hooks("required_apps", app_name="cencomun_erp") == ["erpnext"]
    evidence = {
        "installed_apps": installed,
        "versions": {"frappe": frappe.__version__, "erpnext": erpnext.__version__,
                     "cencomun_erp": cencomun_erp.__version__},
        "module_registration": "passed",
        "database_version": frappe.db.sql("SELECT VERSION()")[0][0],
        "synthetic_user_created": True,
        "api_credentials_generated": True,
    }
    (ROOT / "bootstrap-evidence.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))
finally:
    frappe.destroy()
