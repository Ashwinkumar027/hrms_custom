"""
Locks direct Attendance edits for any date on/before the most recently
closed payroll period (26th-25th), once that period's 26th 11:00 AM passes.
HR Manager / HR User / System Manager are never blocked.
Leave Application and Attendance Request are NOT blocked here — they use
db_set/system writes that bypass this hook entirely (intentional).
"""
from datetime import date, datetime
import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

HR_ROLES = {"HR Manager", "HR User", "System Manager"}
LOCK_HOUR = 11


def check_attendance_lock(doc, method=None):
    if _has_hr_role():
        return

    threshold = _get_lock_threshold()
    if threshold is None:
        return

    if getdate(doc.attendance_date) <= threshold:
        frappe.throw(
            _(
                "Attendance for <b>{0}</b> cannot be modified directly. "
                "The payroll period ending <b>{1}</b> is locked. "
                "Please contact HR."
            ).format(doc.attendance_date, threshold.strftime("%d-%b-%Y")),
            title=_("Attendance Period Locked"),
        )


def _get_lock_threshold():
    """Returns the latest period-end (25th) date that is already locked,
    or None if no period is locked yet."""
    today_dt = now_datetime()
    today = today_dt.date()

    this_month_end = date(today.year, today.month, 25)
    lock_activation = datetime(today.year, today.month, 26, LOCK_HOUR, 0, 0)

    if today_dt >= lock_activation:
        return this_month_end

    # not yet locked this month -> previous period is the locked one
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1
    return date(prev_year, prev_month, 25)


def _has_hr_role():
    return bool(set(frappe.get_roles(frappe.session.user)) & HR_ROLES)


def check_leave_application_lock(doc, method=None):
    threshold = _get_lock_threshold()
    if threshold is None:
        return
    if getdate(doc.to_date) <= threshold or getdate(doc.from_date) <= threshold:
        frappe.throw(
            _("Leave Application cannot be submitted for dates on or before <b>{0}</b>. "
              "That payroll period is locked. Please contact HR.").format(
                  threshold.strftime("%d-%b-%Y")),
            title=_("Payroll Period Locked"),
        )


def check_attendance_request_lock(doc, method=None):
    threshold = _get_lock_threshold()
    if threshold is None:
        return
    if getdate(doc.to_date) <= threshold or getdate(doc.from_date) <= threshold:
        frappe.throw(
            _("Attendance Request cannot be submitted for dates on or before <b>{0}</b>. "
              "That payroll period is locked. Please contact HR.").format(
                  threshold.strftime("%d-%b-%Y")),
            title=_("Payroll Period Locked"),
        )
