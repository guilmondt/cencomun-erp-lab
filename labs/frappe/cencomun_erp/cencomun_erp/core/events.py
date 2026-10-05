"""Durable LAB outbox. At-least-once transport; consumer deduplicates event_id."""

import json, urllib.request
import frappe
from cencomun_erp.core.business import save


def deliver(replay=False):
    if not frappe.conf.get("ccm_lab_enabled"):
        frappe.throw("LAB only", frappe.PermissionError)
    result = {"attempted": 0, "delivered": 0, "failed": 0}
    rows = frappe.get_all(
        "CCM Event", filters={} if replay else {"delivered": 0}, pluck="name"
    )
    for name in rows:
        doc = frappe.get_doc("CCM Event", name)
        doc.attempts += 1
        result["attempted"] += 1
        try:
            request = urllib.request.Request(
                "http://127.0.0.1:8091",
                data=doc.payload.encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=3) as response:
                if response.status != 200:
                    raise ValueError("Consumer rejected")
            doc.delivered = 1
            result["delivered"] += 1
        except Exception:
            result["failed"] += 1
        save(doc)
        frappe.db.commit()
    return result
