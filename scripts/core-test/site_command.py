"""Execute one repository script using a real isolated Frappe connection."""

import os, runpy, sys
from pathlib import Path
import frappe

ROOT = Path("/workspace/.local/frappe-integral")
os.chdir(ROOT / "bench/sites")
frappe.init(
    site=os.environ.get("CCM_CORE_SITE", "ccm-core.test"),
    sites_path=str(ROOT / "bench/sites"),
)
frappe.connect()
try:
    frappe.set_user("Administrator")
    runpy.run_path(sys.argv[1], run_name="__main__")
finally:
    frappe.destroy()
