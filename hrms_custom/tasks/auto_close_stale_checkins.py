import frappe
from frappe.utils import get_datetime, add_to_date, getdate, now_datetime


def execute():
    if frappe.conf.get("disable_checkout_window_guard"):
        return

    stale_ins = frappe.db.sql("""
        SELECT ec.name, ec.employee, ec.time, ec.shift
        FROM `tabEmployee Checkin` ec
        WHERE ec.log_type = 'IN'
          AND IFNULL(ec.custom_auto_closed, 0) = 0
          AND ec.shift IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM `tabEmployee Checkin` ec2
              WHERE ec2.employee = ec.employee
                AND ec2.log_type = 'OUT'
                AND ec2.time > ec.time
                AND DATE(ec2.time) = DATE(ec.time)
          )
    """, as_dict=True)

    for log in stale_ins:
        try:
            _close_if_window_passed(log)
        except Exception:
            frappe.log_error(
                title=f"Auto-close stale checkin failed: {log.name}",
                message=frappe.get_traceback(),
            )


def _close_if_window_passed(log):
    shift = frappe.db.get_value(
        "Shift Type",
        log.shift,
        ["end_time", "allow_check_out_after_shift_end_time"],
        as_dict=True,
    )
    if not shift:
        return

    shift_date = getdate(log.time)
    shift_end = get_datetime(f"{shift_date} {shift.end_time}")
    cutoff = add_to_date(shift_end, minutes=shift.allow_check_out_after_shift_end_time or 0)

    if now_datetime() <= cutoff:
        return

    if frappe.db.exists("Employee Checkin", {
        "employee": log.employee,
        "time": cutoff,
        "custom_auto_closed": 1,
    }):
        return

    out_doc = frappe.new_doc("Employee Checkin")
    out_doc.employee = log.employee
    out_doc.log_type = "OUT"
    out_doc.time = cutoff
    out_doc.custom_auto_closed = 1
    out_doc.skip_auto_attendance = 0
    out_doc.flags.ignore_permissions = True
    out_doc.insert()

    frappe.db.commit()
