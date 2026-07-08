import frappe
from frappe.utils import getdate, nowdate

LOG_PREFIX = "[ForceAbsentMissingCheckout]"
ABSENT_REASON = "Missing final checkout (auto-closed by scheduler)"


def execute():
    today = getdate(nowdate())

    candidates = frappe.get_all(
        "Attendance",
        filters={
            "docstatus": 1,
            "attendance_date": ["<", today],
            "status": ["in", ["Present", "Half Day"]],
            "custom_absent_due_to_missing_checkout": ["!=", 1],
        },
        fields=["name", "employee", "employee_name", "attendance_date"],
    )

    if not candidates:
        _log("No candidates found.")
        return

    corrected = 0

    for att in candidates:
        try:
            if _last_checkout_was_auto_closed(att.name):
                if _force_absent(att):
                    corrected += 1
        except Exception:
            frappe.log_error(
                title=f"{LOG_PREFIX} Failed for {att.name}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()
    _log(f"Done - checked {len(candidates)}, corrected {corrected} to Absent.")


def _last_checkout_was_auto_closed(attendance_name):
    last_out = frappe.get_all(
        "Employee Checkin",
        filters={"attendance": attendance_name, "log_type": "OUT"},
        fields=["name", "custom_auto_closed"],
        order_by="time desc, creation desc, name desc",
        limit_page_length=1,
    )

    if not last_out:
        return False

    return bool(cint_safe(last_out[0].custom_auto_closed))


def cint_safe(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _force_absent(att):
    _locked = frappe.db.sql(
        "SELECT docstatus FROM `tabAttendance` WHERE name=%s FOR UPDATE",
        att.name,
    )
    current_docstatus = _locked[0][0] if _locked else None
    if current_docstatus != 1:
        _log(f"Skipped {att.name} - docstatus changed to {current_docstatus} before update")
        return False

    frappe.db.set_value(
        "Attendance",
        att.name,
        {
            "status": "Absent",
            "late_entry": 0,
            "early_exit": 0,
            "custom_absent_due_to_missing_checkout": 1,
            "custom_absent_reason": ABSENT_REASON,
        },
        update_modified=False,
    )
    return True


def _log(msg):
    frappe.logger("force_absent_missing_checkout").info(f"{LOG_PREFIX} {msg}")
