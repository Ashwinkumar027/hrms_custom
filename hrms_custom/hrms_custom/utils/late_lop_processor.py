from datetime import date
import frappe
from frappe.utils import getdate, nowdate

DEFAULT_GRACE_DAYS = 5
LOP_LEAVE_TYPE     = "Loss of Pay"
LOG_PREFIX         = "[LateLOP]"


def process_late_deductions(period_start=None, period_end=None):
    if not period_start or not period_end:
        period_start, period_end = _get_completed_period()

    period_start = getdate(period_start)
    period_end   = getdate(period_end)
    _log(f"Starting — period {period_start} to {period_end}")

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "company", "leave_approver"],
    )

    success_count = skip_count = error_count = 0

    for emp in employees:
        try:
            created = _process_employee(emp, period_start, period_end)
            if created:
                success_count += created
            else:
                skip_count += 1
        except Exception:
            error_count += 1
            frappe.log_error(
                title=f"{LOG_PREFIX} Failed for {emp.employee_name}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()
    _log(f"Done — created: {success_count} | within limit: {skip_count} | errors: {error_count}")


def _process_employee(emp, period_start, period_end):
    grace_days = _get_grace_days(emp.name, period_end)

    late_records = frappe.get_all(
        "Attendance",
        filters={
            "employee"       : emp.name,
            "late_entry"     : 1,
            "attendance_date": ["between", [period_start, period_end]],
            "docstatus"      : 1,
        },
        fields=["name", "attendance_date"],
        order_by="attendance_date asc",
    )

    total_lates = len(late_records)

    if total_lates <= grace_days:
        return 0

    excess_records = late_records[grace_days:]
    created = 0

    for att in excess_records:
        att_date = getdate(att.attendance_date)

        if _already_lop(att.name):
            continue

        _mark_half_day_lop(att.name, att_date, emp.name)
        created += 1

    if created:
        _log(f"{emp.employee_name}: {total_lates} lates, grace={grace_days}, marked {created} as Half Day LOP")

    return created


def _mark_half_day_lop(att_name, att_date, employee):
    """Directly update attendance to Half Day LOP — no Leave Application conflict."""
    frappe.db.set_value(
        "Attendance",
        att_name,
        {
            "status"    : "Half Day",
            "leave_type": LOP_LEAVE_TYPE,
        },
        update_modified=False,
    )
    _log(f"Marked {employee} attendance {att_date} as Half Day LOP")


def _already_lop(att_name):
    """Check if already marked as LOP to ensure idempotency."""
    status = frappe.db.get_value("Attendance", att_name, ["status", "leave_type"], as_dict=True)
    return status and status.status == "Half Day" and status.leave_type == LOP_LEAVE_TYPE





def _get_completed_period(today=None):
    today = getdate(today or nowdate())

    if today.month == 1:
        end_year, end_month = today.year - 1, 12
    else:
        end_year, end_month = today.year, today.month - 1

    period_end = date(end_year, end_month, 25)

    if end_month == 1:
        start_year, start_month = end_year - 1, 12
    else:
        start_year, start_month = end_year, end_month - 1

    return date(start_year, start_month, 26), period_end


def _get_grace_days(employee, period_end):
    shift = frappe.db.get_value(
        "Shift Assignment",
        {"employee": employee, "docstatus": 1, "start_date": ["<=", period_end]},
        "shift_type",
        order_by="start_date desc",
    )
    if not shift:
        shift = frappe.db.get_value("Employee", employee, "default_shift")
    if not shift:
        return DEFAULT_GRACE_DAYS

    grace = frappe.db.get_value("Shift Type", shift, "custom_late_entry_grace_days")
    return int(grace or DEFAULT_GRACE_DAYS)


def _lop_leave_exists(employee, att_date):
    return frappe.db.exists("Leave Application", {
        "employee"  : employee,
        "leave_type": LOP_LEAVE_TYPE,
        "from_date" : att_date,
        "to_date"   : att_date,
        "half_day"  : 1,
        "docstatus" : ["!=", 2],
    })


def _log(msg):
    frappe.logger("late_lop_processor").info(f"{LOG_PREFIX} {msg}")
