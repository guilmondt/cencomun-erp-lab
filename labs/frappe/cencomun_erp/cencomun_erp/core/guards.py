"""Server guards for lab entities and native product extensions."""

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import frappe
from frappe.model.document import Document


def decimal(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise InvalidOperation
        return number
    except (InvalidOperation, ValueError, TypeError):
        frappe.throw("Invalid decimal", frappe.ValidationError)


def money(value):
    return format(
        decimal(value).quantize(Decimal(".01"), rounding=ROUND_HALF_UP), ".2f"
    )


@contextmanager
def service():
    old = frappe.flags.ccm_service
    frappe.flags.ccm_service = True
    try:
        yield
    finally:
        frappe.flags.ccm_service = old


class ProtectedDocument(Document):
    def validate(self):
        if not frappe.flags.ccm_service:
            frappe.throw("Use the authorized Cencomun service", frappe.PermissionError)

    def on_trash(self):
        frappe.throw(
            "Laboratory history cannot be erased through document deletion",
            frappe.PermissionError,
        )


class ImmutableAudit(ProtectedDocument):
    def validate(self):
        super().validate()
        if not self.is_new():
            frappe.throw("Audit is immutable", frappe.PermissionError)


class CashClosing(ProtectedDocument):
    def validate(self):
        super().validate()
        old = self.get_doc_before_save()
        if old and old.state == "CONFIRMED":
            frappe.throw("Confirmed closing is immutable", frappe.ValidationError)


def validate_item(doc, method=None):
    old = doc.get_doc_before_save()
    if old and old.get("ccm_company") and (old.ccm_company != doc.ccm_company or old.ccm_id != doc.ccm_id):
        frappe.throw("Scoped product identity is immutable", frappe.PermissionError)
    if not doc.get("ccm_company"):
        return
    if not frappe.conf.get("ccm_lab_enabled"):
        frappe.throw("Cencomun Core Test is LAB-only", frappe.PermissionError)
    price = decimal(doc.cashea_price or "0")
    if price <= 0 or price.as_tuple().exponent < -2:
        frappe.throw("Ordinary price must be positive with at most two decimals")
    warranty = decimal(doc.warranty_quantity or "0")
    if warranty < 0 or warranty != warranty.to_integral_value():
        frappe.throw("Warranty must be a nonnegative integer")
    if doc.warranty_unit not in ["DAY", "MONTH", "YEAR"]:
        frappe.throw("Invalid warranty unit")
    if doc.ccm_condition not in ["NEW", "USED", "REFURBISHED"]:
        frappe.throw("Invalid condition")
    if frappe.session.user != "Administrator":
        from cencomun_erp.core.business import access

        access(doc.ccm_company, ["CCM Operator"])


def native_write_guard(doc, method=None):
    """Native draft factories need create rights, but posting stays service-only.

    This hook is installed as app code, not an upstream change. Site admin may
    load synthetic fixtures; business actors must enter the authorized service.
    """
    if doc.get("company") != frappe.conf.get("ccm_company") or not frappe.conf.get(
        "ccm_lab_enabled"
    ):
        return
    if frappe.session.user != "Administrator" and not frappe.flags.ccm_service:
        frappe.throw(
            "Native financial/stock writes require the authorized CCM service",
            frappe.PermissionError,
        )
