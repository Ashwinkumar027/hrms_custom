from frappe.utils import add_days, formatdate, getdate, today

import frappe
from hrms_custom.utils.email_utils import get_hr_sender


VALID_ATTENDANCE_STATUSES = ("Present", "Half Day", "Work From Home", "On Leave")


def send_missing_attendance_emails_for_yesterday():
    if not frappe.db.get_single_value("HR Settings", "custom_enable_missing_attendance_email"):
        frappe.logger("hrms_custom").info(
            "Missing attendance email skipped: custom_enable_missing_attendance_email is not enabled."
        )
        return {"skipped_reason": "disabled_in_hr_settings"}

    attendance_date = getdate(add_days(today(), -1))
    return send_missing_attendance_emails(attendance_date=attendance_date)


def send_missing_attendance_emails(attendance_date=None, dry_run=False, employee=None):
    attendance_date = getdate(attendance_date or add_days(today(), -1))
    result = {
        "attendance_date": str(attendance_date),
        "dry_run": bool(dry_run),
        "employee": employee,
        "checked": 0,
        "queued": 0,
        "skipped": 0,
        "employees": [],
    }

    employee_filters = {"status": "Active"}
    if employee:
        employee_filters["name"] = employee

    employees = frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=[
            "name",
            "employee_name",
            "company",
            "date_of_joining",
            "relieving_date",
            "holiday_list",
            "user_id",
            "company_email",
            "personal_email",
            "prefered_email",
            "prefered_contact_email",
            "reports_to",
        ],
        order_by="name",
    )

    for employee in employees:
        result["checked"] += 1

        if not _is_employee_active_on_date(employee, attendance_date):
            result["skipped"] += 1
            continue
        if not _has_active_shift_assignment(employee.name, attendance_date):
            result["skipped"] += 1
            continue

        if _has_valid_attendance(employee.name, attendance_date):
            result["skipped"] += 1
            continue

        if _has_approved_leave(employee.name, attendance_date):
            result["skipped"] += 1
            continue

        if _is_regular_holiday(employee, attendance_date):
            result["skipped"] += 1
            continue

        recipient = _get_employee_email(employee)
        if not recipient:
            result["skipped"] += 1
            continue

        subject = _get_subject(employee, attendance_date)
        if _already_queued(employee.name):
            result["skipped"] += 1
            continue

        result["employees"].append(
            {
                "employee": employee.name,
                "employee_name": employee.employee_name,
                "email": recipient,
                "subject": subject,
            }
        )

        if not dry_run:
            _send_missing_attendance_email(employee, recipient, attendance_date, subject)

        result["queued"] += 1

    frappe.logger("hrms_custom").info(
        "Missing attendance email result for {0}: {1}".format(attendance_date, result)
    )
    return result


def _is_employee_active_on_date(employee, attendance_date):
    if employee.date_of_joining and getdate(employee.date_of_joining) > attendance_date:
        return False

    if employee.relieving_date and getdate(employee.relieving_date) < attendance_date:
        return False

    return True


def _has_valid_attendance(employee, attendance_date):
    return frappe.db.exists(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": attendance_date,
            "docstatus": ["!=", 2],
            "status": ["in", VALID_ATTENDANCE_STATUSES],
        },
    )


def _has_active_shift_assignment(employee, attendance_date):
    rows = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": employee,
            "docstatus": 1,
            "status": "Active",
            "start_date": ["<=", attendance_date],
        },
        or_filters=[
            ["end_date", ">=", attendance_date],
            ["end_date", "is", "not set"],
        ],
        limit_page_length=1,
    )
    return bool(rows)


def _has_approved_leave(employee, attendance_date):
    return frappe.db.exists(
        "Leave Application",
        {
            "employee": employee,
            "from_date": ["<=", attendance_date],
            "to_date": [">=", attendance_date],
            "status": "Approved",
            "docstatus": 1,
        },
    )


def _is_regular_holiday(employee, attendance_date):
    if _is_optional_holiday(employee.company, attendance_date):
        return False

    holiday_list = employee.holiday_list or _get_company_holiday_list(employee.company)
    if not holiday_list:
        return False

    return bool(
        frappe.db.exists(
            "Holiday",
            {
                "parent": holiday_list,
                "parenttype": "Holiday List",
                "holiday_date": attendance_date,
            },
        )
    )


def _is_optional_holiday(company, attendance_date):
    filters = {
        "is_active": 1,
        "from_date": ["<=", attendance_date],
        "to_date": [">=", attendance_date],
        "optional_holiday_list": ["is", "set"],
    }

    if company:
        filters["company"] = ["in", [company, ""]]

    leave_periods = frappe.get_all(
        "Leave Period",
        filters=filters,
        fields=["optional_holiday_list"],
    )

    for leave_period in leave_periods:
        if frappe.db.exists(
            "Holiday",
            {
                "parent": leave_period.optional_holiday_list,
                "parenttype": "Holiday List",
                "holiday_date": attendance_date,
            },
        ):
            return True

    return False


def _get_company_holiday_list(company):
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_holiday_list")


def _get_employee_email(employee):
    return (
        employee.company_email
        or employee.prefered_email
        or employee.prefered_contact_email
        or employee.personal_email
        or frappe.db.get_value("User", employee.user_id, "email")
    )

def _get_subject(employee, attendance_date):
    return "Missing Attendance Reminder - {0} - {1}".format(
        employee.name,
        attendance_date,
    )


def _already_queued(employee_name):
    return bool(
        frappe.db.exists(
            "Email Queue",
            {
                "reference_doctype": "Employee",
                "reference_name": employee_name,
                "creation": ["between", [today() + " 00:00:00", today() + " 23:59:59"]],
            },
        )
    )


def _get_checkin_summary(employee, attendance_date):
    """Returns info about real (non-auto-closed) checkins for this employee/date."""
    logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [
                str(attendance_date) + " 00:00:00",
                str(attendance_date) + " 23:59:59",
            ]],
        },
        fields=["log_type", "time", "custom_auto_closed"],
        order_by="time asc",
    )

    real_logs = [l for l in logs if not l.custom_auto_closed]
    has_in = any(l.log_type == "IN" for l in real_logs)
    has_out = any(l.log_type == "OUT" for l in real_logs)
    first_in_time = next((l.time for l in real_logs if l.log_type == "IN"), None)

    return {
        "has_in": has_in,
        "has_out": has_out,
        "first_in_time": first_in_time,
    }


def _get_manager_email(employee):
    if not employee.reports_to:
        return None

    manager = frappe.db.get_value(
        "Employee",
        employee.reports_to,
        ["company_email", "prefered_email", "prefered_contact_email", "personal_email", "user_id"],
        as_dict=True,
    )
    if not manager:
        return None

    return (
        manager.company_email
        or manager.prefered_email
        or manager.prefered_contact_email
        or manager.personal_email
        or (frappe.db.get_value("User", manager.user_id, "email") if manager.user_id else None)
    )


def _send_missing_attendance_email(employee, recipient, attendance_date, subject):
    formatted_date = formatdate(attendance_date)
    checkin_summary = _get_checkin_summary(employee.name, attendance_date)

    if checkin_summary["has_in"] and not checkin_summary["has_out"]:
        from frappe.utils import format_time
        checkin_time = format_time(checkin_summary["first_in_time"])
        body_line = (
            "<p>You checked in on <b>{0}</b> at {1}, but no checkout was recorded. "
            "This day could not be counted as Present.</p>"
        ).format(formatted_date, checkin_time)
    else:
        body_line = (
            "<p>No attendance record was found for <b>{0}</b>.</p>"
        ).format(formatted_date)

    cc_list = []
    manager_email = _get_manager_email(employee)
    if manager_email and manager_email != recipient:
        cc_list.append(manager_email)

    frappe.sendmail(
        recipients=[recipient],
        cc=cc_list,
        subject=subject,
        message=(
            "<p>Dear {0},</p>"
            "{1}"
            "<p>If you were working on this date, please regularize your attendance or contact HR.</p>"
            "<p>Regards,<br>HR Team</p>"
        ).format(employee.employee_name or employee.name, body_line),
        reference_doctype="Employee",
        reference_name=employee.name,
        sender=get_hr_sender(),
    )
