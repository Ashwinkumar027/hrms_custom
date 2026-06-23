"""
lop_summary_email.py
────────────────────
Runs daily via scheduler. Fires only on the 25th of every month.

Sends each active employee a LOP summary for the closing payroll period
(26th of previous month → 25th of current month).

LOP definition (matches late_lop_processor.py exactly):
  • Any Attendance with status = 'Absent' (docstatus=1) → full-day LOP
  • Any Attendance with status = 'Half Day' AND leave_type in any
    Leave Type flagged Is Leave Without Pay (is_lwp=1) → half-day LOP

Leave Type names are resolved dynamically via is_lwp=1 — never hardcoded.
Confirmed on this system: both "Loss of Pay" and "Leave Without Pay" are
valid is_lwp=1 records, so a hardcoded single name would silently miss one.

Grace-day numbers are imported directly from late_lop_processor so the
email always matches what was actually applied — no duplicated logic.

Email content:
  • Total LOP days
  • Each LOP date with status (Half Day / Absent)
  • Running total of late entries that caused LOP

Reporting Manager is added to CC.
Zero-LOP employees receive an "all clear" email.
Dedupe: skips sending if a LOP summary email was already queued today
for this employee (subject-scoped, so it doesn't collide with the
unrelated missing-attendance dedupe check on the same Employee record).
"""

from datetime import date

import frappe
from frappe.utils import getdate, formatdate, nowdate

from hrms_custom.hrms_custom.utils.late_lop_processor import _get_grace_days


LOG_PREFIX = "[LOPEmail]"
SUBJECT_MARKER = "Payroll LOP Summary"


# ─────────────────────────────────────────────────────────────
# SCHEDULER ENTRY POINT
# ─────────────────────────────────────────────────────────────

def send_lop_summary_emails():
    """
    Called by scheduler daily.
    Only executes on the 25th of every month, and only if
    enable_lop_summary_email is set in site_config.
    """
    if not frappe.conf.get("enable_lop_summary_email"):
        frappe.logger("hrms_custom").info(
            "LOP summary email skipped: enable_lop_summary_email is not enabled."
        )
        return {"skipped_reason": "disabled_in_site_config"}

    today = getdate(nowdate())
    if today.day != 25:
        return

    _log(f"25th detected — running LOP summary emails for period ending {today}")

    period_start, period_end = _get_period(today)
    lwp_types = _get_lwp_leave_types()
    _log(f"Period: {period_start} → {period_end} | LWP leave types: {lwp_types}")

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=[
            "name",
            "employee_name",
            "company",
            "company_email",
            "personal_email",
            "prefered_email",
            "prefered_contact_email",
            "user_id",
            "reports_to",
            "date_of_joining",
            "relieving_date",
        ],
    )

    sent = skipped = errors = 0

    for emp in employees:
        try:
            ok = _process_employee(emp, period_start, period_end, lwp_types)
            if ok:
                sent += 1
            else:
                skipped += 1
        except Exception:
            errors += 1
            frappe.log_error(
                title=f"{LOG_PREFIX} Failed for {emp.employee_name} ({emp.name})",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()
    _log(f"Done — sent: {sent} | skipped: {skipped} | errors: {errors}")


# ─────────────────────────────────────────────────────────────
# PER-EMPLOYEE PROCESSING
# ─────────────────────────────────────────────────────────────

def _process_employee(emp, period_start, period_end, lwp_types):
    if emp.date_of_joining and getdate(emp.date_of_joining) > period_end:
        return False
    if emp.relieving_date and getdate(emp.relieving_date) < period_start:
        return False

    recipient = _get_email(emp)
    if not recipient:
        _log(f"No email found for {emp.employee_name} ({emp.name}) — skipping")
        return False

    if _already_queued(emp.name):
        _log(f"Already queued today for {emp.employee_name} ({emp.name}) — skipping")
        return False

    lop_records = _get_lop_records(emp.name, period_start, period_end, lwp_types)
    lop_days = len(lop_records)

    late_records = frappe.get_all(
        "Attendance",
        filters={
            "employee": emp.name,
            "late_entry": 1,
            "attendance_date": ["between", [period_start, period_end]],
            "docstatus": 1,
        },
        fields=["attendance_date"],
        order_by="attendance_date asc",
    )
    total_lates = len(late_records)
    grace_days = _get_grace_days(emp.name, period_end)
    lop_causing_lates = max(0, total_lates - grace_days)

    cc_email = _get_manager_email(emp.reports_to)

    subject = _build_subject(emp, period_start, period_end, lop_days)
    body = _build_body(
        emp, period_start, period_end,
        lop_days, lop_records,
        total_lates, grace_days, lop_causing_lates,
    )

    send_kwargs = dict(
        recipients=[recipient],
        subject=subject,
        message=body,
        reference_doctype="Employee",
        reference_name=emp.name,
    )
    if cc_email:
        send_kwargs["cc"] = [cc_email]

    frappe.sendmail(**send_kwargs)
    _log(
        f"Sent to {recipient}"
        + (f" CC {cc_email}" if cc_email else "")
        + f" | {emp.employee_name} | LOP={lop_days} | Lates={total_lates}"
    )
    return True


# ─────────────────────────────────────────────────────────────
# LOP RECORD RESOLUTION (dynamic leave-type aware)
# ─────────────────────────────────────────────────────────────

def _get_lwp_leave_types():
    """All Leave Types flagged Is Leave Without Pay. Resolved fresh each run —
    never hardcode names, this system has more than one (Loss of Pay,
    Leave Without Pay) and may add more later."""
    return frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name")


def _get_lop_records(employee, period_start, period_end, lwp_types):
    """
    LOP = any Absent record, OR any Half Day record whose leave_type is
    flagged is_lwp=1. Matches late_lop_processor's actual write behavior:
    full-day LOP is written as status='Absent' with leave_type left blank,
    half-day LOP is written as status='Half Day' with leave_type set.
    """
    safe_lwp_types = lwp_types or [""]

    return frappe.db.sql("""
        select attendance_date, status, leave_type
        from `tabAttendance`
        where employee = %(employee)s
          and docstatus = 1
          and attendance_date between %(start)s and %(end)s
          and (
                status = 'Absent'
                or (status = 'Half Day' and leave_type in %(lwp_types)s)
          )
        order by attendance_date asc
    """, {
        "employee": employee,
        "start": period_start,
        "end": period_end,
        "lwp_types": safe_lwp_types,
    }, as_dict=True)


# ─────────────────────────────────────────────────────────────
# EMAIL CONTENT BUILDERS
# ─────────────────────────────────────────────────────────────

def _build_subject(emp, period_start, period_end, lop_days):
    status = "All Clear" if lop_days == 0 else f"{lop_days} LOP Day(s)"
    return (
        f"{SUBJECT_MARKER} — {emp.employee_name} ({emp.name})"
        f" | {formatdate(period_start)} to {formatdate(period_end)}"
        f" | {status}"
    )


def _build_body(emp, period_start, period_end, lop_days, lop_records,
                total_lates, grace_days, lop_causing_lates):

    if lop_records:
        lop_rows = ""
        for i, rec in enumerate(lop_records, 1):
            lop_rows += (
                f"<tr>"
                f"<td style='{_td}'>{i}</td>"
                f"<td style='{_td}'>{formatdate(rec.attendance_date)}</td>"
                f"<td style='{_td}'>{rec.status}</td>"
                f"</tr>"
            )
    else:
        lop_rows = (
            f"<tr><td colspan='3' style='{_td} text-align:center; color:#2e7d32;'>"
            f"No LOP days — you're all clear this period!</td></tr>"
        )

    late_summary_color = "#c62828" if lop_causing_lates > 0 else "#1b5e20"
    late_rows = f"""
        <tr>
            <td style='{_td}'>Total late entries this period</td>
            <td style='{_td}'>{total_lates}</td>
        </tr>
        <tr>
            <td style='{_td}'>Grace days allowed (no penalty)</td>
            <td style='{_td}'>{grace_days}</td>
        </tr>
        <tr>
            <td style='{_td}'><strong>Late entries that caused LOP</strong></td>
            <td style='{_td} color:{late_summary_color};'><strong>{lop_causing_lates}</strong></td>
        </tr>
    """

    if lop_days == 0:
        banner_bg = "#e8f5e9"
        banner_color = "#1b5e20"
        banner_text = "No Loss of Pay this period. Great work!"
    else:
        banner_bg = "#fff3e0"
        banner_color = "#e65100"
        banner_text = (
            f"Total LOP Days: <strong>{lop_days}</strong>. "
            f"These will be deducted from your salary for this period."
        )

    return f"""
<p style="font-family:Arial,sans-serif; font-size:14px;">Dear <strong>{emp.employee_name}</strong>,</p>

<p style="font-family:Arial,sans-serif; font-size:14px;">
Please find your <strong>Loss of Pay (LOP) summary</strong> for the payroll period
<strong>{formatdate(period_start)}</strong> to <strong>{formatdate(period_end)}</strong>.
</p>

<div style="background:{banner_bg}; color:{banner_color}; padding:12px 16px;
            border-radius:4px; font-family:Arial,sans-serif; font-size:14px; margin-bottom:16px;">
    {banner_text}
</div>

<p style="font-family:Arial,sans-serif; font-size:13px; font-weight:bold; margin-bottom:4px;">
    LOP Date Breakdown
</p>
<table style="border-collapse:collapse; min-width:420px;
              font-family:Arial,sans-serif; font-size:13px; margin-bottom:20px;">
    <thead>
        <tr style="background:#f5f5f5;">
            <th style="{_th}">#</th>
            <th style="{_th}">Date</th>
            <th style="{_th}">Attendance Status</th>
        </tr>
    </thead>
    <tbody>
        {lop_rows}
    </tbody>
    <tfoot>
        <tr style="background:#fafafa;">
            <td colspan="2" style="{_td} font-weight:bold;">Total LOP Days</td>
            <td style="{_td} font-weight:bold;">{lop_days}</td>
        </tr>
    </tfoot>
</table>

<p style="font-family:Arial,sans-serif; font-size:13px; font-weight:bold; margin-bottom:4px;">
    Late Entry Summary
</p>
<table style="border-collapse:collapse; min-width:420px;
              font-family:Arial,sans-serif; font-size:13px; margin-bottom:20px;">
    <tbody>
        {late_rows}
    </tbody>
</table>

<p style="font-family:Arial,sans-serif; font-size:13px; color:#555;">
    If you believe any record is incorrect, please raise an
    <strong>Attendance Request</strong> or <strong>Leave Application</strong>
    before end of day today (<strong>{formatdate(period_end)}</strong>).
    After today, the period will be locked for payroll processing.
</p>

<p style="font-family:Arial,sans-serif; font-size:13px;">
    Regards,<br><strong>HR Team</strong>
</p>
"""


_td = "padding:6px 12px; border:1px solid #ddd;"
_th = "padding:8px 12px; border:1px solid #ddd; text-align:left; font-weight:bold;"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _get_period(today):
    period_end = date(today.year, today.month, 25)
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1
    period_start = date(prev_year, prev_month, 26)
    return period_start, period_end


def _get_email(emp):
    return (
        emp.company_email
        or emp.prefered_email
        or emp.prefered_contact_email
        or emp.personal_email
        or (frappe.db.get_value("User", emp.user_id, "email") if emp.user_id else None)
    )


def _get_manager_email(reports_to):
    if not reports_to:
        return None
    mgr = frappe.db.get_value(
        "Employee",
        reports_to,
        ["company_email", "prefered_email", "personal_email", "user_id"],
        as_dict=True,
    )
    if not mgr:
        return None
    return (
        mgr.company_email
        or mgr.prefered_email
        or mgr.personal_email
        or (frappe.db.get_value("User", mgr.user_id, "email") if mgr.user_id else None)
    )


def _already_queued(employee_name):
    """
    Subject-scoped dedupe — deliberately NOT a bare reference_doctype/
    reference_name check like missing_attendance_email's _already_queued,
    because both features queue against the same Employee record on the
    same day (the 25th), and a bare check would falsely skip this email
    after the unrelated missing-attendance email already queued today.
    """
    return bool(
        frappe.db.exists(
            "Email Queue",
            {
                "reference_doctype": "Employee",
                "reference_name": employee_name,
                "subject": ["like", f"%{SUBJECT_MARKER}%"],
                "creation": ["between", [
                    frappe.utils.today() + " 00:00:00",
                    frappe.utils.today() + " 23:59:59",
                ]],
            },
        )
    )


def _log(msg):
    frappe.logger("lop_summary_email").info(f"{LOG_PREFIX} {msg}")
