import frappe
from frappe import _

def validate_probation_status(doc, method=None):
    """
    Auto-sync and validate Probation Status on Employee:
    1. If final_confirmation_date is filled, auto-set custom_probation_status to 'Confirmed'.
    2. Only HR Manager, System Manager, and Administrator can manually change custom_probation_status.
    """
    if doc.final_confirmation_date and doc.get("custom_probation_status") != "Confirmed":
        doc.custom_probation_status = "Confirmed"

    if doc.is_new():
        if not doc.get("custom_probation_status"):
            doc.custom_probation_status = "Confirmed" if doc.final_confirmation_date else "Not Confirmed"
        return

    # Enforce role restriction on manual edits
    old_status = doc.get_db_value("custom_probation_status")
    new_status = doc.get("custom_probation_status")

    if old_status and new_status and old_status != new_status:
        user = frappe.session.user
        if user and user not in ("Administrator",) and not getattr(frappe.flags, "in_patch", False):
            user_roles = frappe.get_roles(user)
            allowed_roles = {"HR Manager", "System Manager", "Administrator"}
            if not allowed_roles.intersection(user_roles):
                frappe.throw(
                    _("Only HR Manager can modify Probation Status."),
                    frappe.PermissionError
                )
