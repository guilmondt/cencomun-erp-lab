"""Versioned role/field/workflow installation, safe to repeat."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

ROLES = [
    "CCM Reader",
    "CCM Operator",
    "CCM Buyer",
    "CCM Manager",
    "CCM Director",
    "CCM Simulator",
    "CCM MCP",
]


def install():
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role, "desk_access": 1}
            ).insert(ignore_permissions=True)
    specs = [
        ("ccm_company", "Link", "Company"),
        ("ccm_id", "Data", None),
        ("marketplace_enabled", "Check", None),
        ("cashea_enabled", "Check", None),
        ("cashea_price", "Currency", None),
        ("supplier_reference", "Data", None),
        ("warranty_quantity", "Int", None),
        ("warranty_unit", "Select", "DAY\nMONTH\nYEAR"),
        ("ccm_condition", "Select", "NEW\nUSED\nREFURBISHED"),
    ]
    create_custom_fields(
        {
            "Item": [
                {
                    "fieldname": n,
                    "label": n.replace("_", " ").title(),
                    "fieldtype": t,
                    **({"options": o} if o else {}),
                    "insert_after": "item_name",
                }
                for n, t, o in specs
            ],
            "Customer": [
                {
                    "fieldname": "ccm_company",
                    "label": "CCM Company",
                    "fieldtype": "Link",
                    "options": "Company",
                    "insert_after": "customer_name",
                },
                {
                    "fieldname": "ccm_id",
                    "label": "CCM fixture ID",
                    "fieldtype": "Data",
                    "unique": 1,
                    "insert_after": "customer_name",
                },
            ],
        }
    )
    from frappe.permissions import add_permission, update_permission_property

    for dt in [
        "Item",
        "Customer",
        "Sales Invoice",
        "Sales Order",
        "Delivery Note",
        "Purchase Order",
        "Bin",
        "Account",
        "GL Entry",
        "Warehouse",
        "Payment Entry",
        "Journal Entry",
        "Bank Transaction",
        "Serial No",
        "Contact",
    ]:
        for role in ROLES:
            add_permission(dt, role, 0)
            update_permission_property(
                dt,
                role,
                0,
                "read",
                int(role != "CCM MCP" or dt in ["Item", "Customer", "Bin", "Account"]),
            )
        update_permission_property(dt, "CCM Operator", 0, "write", int(dt == "Item"))
        for role in ["CCM Operator", "CCM Simulator"]:
            update_permission_property(
                dt,
                role,
                0,
                "create",
                int(dt in ["Delivery Note", "Sales Invoice", "Payment Entry"]),
            )
    if not frappe.db.exists("Workflow", "CCM LAB Purchase"):
        states = [
            {"state": state, "doc_status": 0, "allow_edit": role}
            for state, role in [
                ("Draft", "CCM Operator"),
                ("Pending Buyer", "CCM Buyer"),
                ("Pending Manager", "CCM Manager"),
                ("Pending Director", "CCM Director"),
                ("Approved", "CCM Manager"),
            ]
        ]
        for row in states:
            if not frappe.db.exists("Workflow State", row["state"]):
                frappe.get_doc(
                    {"doctype": "Workflow State", "workflow_state_name": row["state"]}
                ).insert(ignore_permissions=True)
        for name in ["Request Approval", "Approve"]:
            if not frappe.db.exists("Workflow Action Master", name):
                frappe.get_doc(
                    {"doctype": "Workflow Action Master", "workflow_action_name": name}
                ).insert(ignore_permissions=True)
        transitions = []
        for target, condition in [
            ("Pending Buyer", "float(doc.approval_amount) <= 200"),
            ("Pending Manager", "200 < float(doc.approval_amount) <= 1000"),
            ("Pending Director", "float(doc.approval_amount) > 1000"),
        ]:
            transitions.append(
                {
                    "state": "Draft",
                    "action": "Request Approval",
                    "next_state": target,
                    "allowed": "CCM Operator",
                    "condition": condition,
                    "allow_self_approval": 1,
                }
            )
        for state, roles in [
            ("Pending Buyer", ["CCM Buyer", "CCM Manager", "CCM Director"]),
            ("Pending Manager", ["CCM Manager", "CCM Director"]),
            ("Pending Director", ["CCM Director"]),
        ]:
            for role in roles:
                transitions.append(
                    {
                        "state": state,
                        "action": "Approve",
                        "next_state": "Approved",
                        "allowed": role,
                        "allow_self_approval": 0,
                    }
                )
        frappe.get_doc(
            {
                "doctype": "Workflow",
                "workflow_name": "CCM LAB Purchase",
                "document_type": "CCM Purchase Request",
                "is_active": 1,
                "workflow_state_field": "workflow_state",
                "states": states,
                "transitions": transitions,
            }
        ).insert(ignore_permissions=True)

    workflow = frappe.get_doc("Workflow", "CCM LAB Purchase")
    if not frappe.db.exists("Workflow Action Master", "Revise"):
        frappe.get_doc(
            {"doctype": "Workflow Action Master", "workflow_action_name": "Revise"}
        ).insert(ignore_permissions=True)
    if not any(r.action == "Revise" for r in workflow.transitions):
        workflow.append(
            "transitions",
            {
                "state": "Approved",
                "action": "Revise",
                "next_state": "Draft",
                "allowed": "CCM Operator",
                "allow_self_approval": 1,
            },
        )
        workflow.save(ignore_permissions=True)

    from frappe.custom.doctype.property_setter.property_setter import (
        make_property_setter,
    )

    for dt, fields in [
        ("Item", "item_name,supplier_reference,ccm_id"),
        ("Customer", "customer_name,mobile_no,email_id,ccm_id"),
        ("Sales Invoice", "customer_name,po_no"),
    ]:
        make_property_setter(
            dt,
            None,
            "search_fields",
            fields,
            "Data",
            for_doctype=True,
            validate_fields_for_doctype=False,
        )
