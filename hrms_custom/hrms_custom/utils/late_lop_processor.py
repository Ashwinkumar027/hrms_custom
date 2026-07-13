from datetime import date
import frappe
from frappe.utils import getdate, get_datetime, nowdate, cint

DEFAULT_GRACE_DAYS       = 5
DEFAULT_GRACE_TIME_LIMIT = 45   # minutes after shift start; used only if not configured on Shift Type
LOP_LEAVE_TYPE           = "Loss of Pay"
LOG_PREFIX               = "[LateLOP]"


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
    """
    Rules (per Attendance record, status=Present, late_entry=1, docstatus=1):

      minutes_late = in_time - (attendance_date + shift.start_time)

      minutes_late <= late_entry_grace_period                         -> ignore (fully forgiven, defensive guard)
      late_entry_grace_period < minutes_late <= grace_day_time_limit   -> queue for grace-day consumption
      minutes_late > grace_day_time_limit                              -> Half Day + LOP immediately, balance untouched

    Grace-day balance is tracked per Shift Type independently, so an
    employee whose Shift Type changes mid-cycle draws from each shift's
    own allowance rather than a single merged number.
    """
    late_records = frappe.get_all(
        "Attendance",
        filters={
            "employee"       : emp.name,
            "status"         : "Present",
            "late_entry"     : 1,
            "attendance_date": ["between", [period_start, period_end]],
            "docstatus"      : 1,
        },
        fields=["name", "attendance_date", "in_time", "shift"],
        order_by="attendance_date asc",
    )

    if not late_records:
        return 0

    queue = []
    created = 0

    for att in late_records:
        if _already_lop(att.name):
            continue

        shift_cfg = _get_shift_config(att.shift, emp.name, att.attendance_date)
        if not shift_cfg:
            continue

        minutes_late = _get_minutes_late(att, shift_cfg)
        if minutes_late is None:
            continue

        if minutes_late <= shift_cfg.grace_period:
            # Defensive guard — should not normally occur since native HRMS
            # only sets late_entry=1 when minutes_late > grace_period.
            continue

        if minutes_late > shift_cfg.grace_time_limit:
            _mark_half_day_lop(att.name, att.attendance_date, emp.employee_name)
            created += 1
            continue

        att._grace_days = shift_cfg.grace_days
        att._resolved_shift = shift_cfg.resolved_shift_name
        queue.append(att)

    if queue:
        balances = {}  # resolved_shift_name -> remaining balance
        for att in queue:
            shift_name = att._resolved_shift
            if shift_name not in balances:
                balances[shift_name] = att._grace_days

            if balances[shift_name] > 0:
                balances[shift_name] -= 1
                # Forgiven — stays Present, no action needed.
                continue
            _mark_half_day_lop(att.name, att.attendance_date, emp.employee_name)
            created += 1

    if created:
        _log(f"{emp.employee_name}: marked {created} as Half Day LOP for period {period_start}-{period_end}")

    return created


def _get_shift_config(shift, employee, attendance_date):
    """Resolve shift start_time, grace_period, grace_days, grace_time_limit for a given attendance."""
    shift_name = shift
    if not shift_name:
        shift_name = frappe.db.get_value(
            "Shift Assignment",
            {"employee": employee, "docstatus": 1, "start_date": ["<=", attendance_date]},
            "shift_type",
            order_by="start_date desc",
        )
    if not shift_name:
        shift_name = frappe.db.get_value("Employee", employee, "default_shift")
    if not shift_name:
        return None

    shift_doc = frappe.db.get_value(
        "Shift Type",
        shift_name,
        [
            "start_time",
            "late_entry_grace_period",
            "custom_late_entry_grace_days",
            "custom_late_entry_grace_day_time_limit",
        ],
        as_dict=True,
    )
    if not shift_doc:
        return None

    grace_period = cint(shift_doc.late_entry_grace_period)

    raw_time_limit = shift_doc.custom_late_entry_grace_day_time_limit
    grace_time_limit = cint(raw_time_limit) if raw_time_limit is not None else DEFAULT_GRACE_TIME_LIMIT

    raw_grace_days = shift_doc.custom_late_entry_grace_days
    grace_days = cint(raw_grace_days) if raw_grace_days is not None else DEFAULT_GRACE_DAYS

    return frappe._dict(
        resolved_shift_name=shift_name,
        start_time=shift_doc.start_time,
        grace_period=grace_period,
        grace_time_limit=grace_time_limit,
        grace_days=grace_days,
    )


def _get_grace_days(employee, attendance_date):
    """Returns the grace_days allowance for this employee's shift as of
    attendance_date. Thin wrapper around _get_shift_config for callers
    (e.g. lop_summary_email.py) that only need the grace_days figure."""
    shift_cfg = _get_shift_config(None, employee, attendance_date)
    if not shift_cfg:
        return 0
    return shift_cfg.grace_days


def _get_minutes_late(att, shift_cfg):
    if not att.in_time or not shift_cfg.start_time:
        return None

    att_date = getdate(att.attendance_date)
    shift_start_dt = get_datetime(f"{att_date} {shift_cfg.start_time}")
    in_time_dt = get_datetime(att.in_time)

    delta = in_time_dt - shift_start_dt
    return delta.total_seconds() / 60


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


def _log(msg):
    frappe.logger("late_lop_processor").info(f"{LOG_PREFIX} {msg}")
