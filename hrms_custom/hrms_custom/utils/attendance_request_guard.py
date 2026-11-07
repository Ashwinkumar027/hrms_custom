import frappe

FULL_DAY_REASONS = ["Regularization", "On Duty", "Work From Home"]


def has_full_day_request(attendance_name):
    """True if this Attendance is tied to an approved Regularization / On Duty / WFH request."""
    meta = frappe.get_meta("Attendance")
    fields = [f for f in ("custom_attendance_request", "attendance_request") if meta.has_field(f)]
    if not fields:
        return False
    row = frappe.db.get_value("Attendance", attendance_name, fields, as_dict=True)
    if not row:
        return False
    for f in fields:
        req = row.get(f)
        if req:
            data = frappe.db.get_value("Attendance Request", req, ["docstatus", "reason"], as_dict=True)
            if data and data.docstatus == 1 and data.reason in FULL_DAY_REASONS:
                return True
    return False
