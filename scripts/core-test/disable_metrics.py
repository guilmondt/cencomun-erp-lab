import frappe
from frappe.installer import update_site_config
from frappe.recorder import RecorderConfig

update_site_config("ccm_measure_queries", 0)
frappe.conf.ccm_measure_queries = 0
RecorderConfig.delete()
print("LAB query measurement disabled.")
