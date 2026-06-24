from frappe.utils import add_days, formatdate, getdate, today

import frappe
from hrms_custom.utils.email_utils import get_hr_sender


VALID_ATTENDANCE_STATUSES = ("Present", "Half Day", "Work From Home", "On Leave")


def send_missing_attendance_emails_for_yesterday():
    if not frappe.conf.get("enable_missing_attendance_email"):
        frappe.logger("hrms_custom").info(
            "Missing attendance email skipped: enable_missing_attendance_email is not enabled."
        )
        return {"skipped_reason": "disabled_in_site_config"}

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
        ],
        order_by="name",
    )

    for employee in employees:
        result["checked"] += 1

        if not _is_employee_active_on_date(employee, attendance_date):
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


def _send_missing_attendance_email(employee, recipient, attendance_date, subject):
    formatted_date = formatdate(attendance_date)

    frappe.sendmail(
        recipients=[recipient],
        subject=subject,
        message=(
            "<p>Dear {0},</p>"
            "<p>Attendance is not marked as Present for <b>{1}</b>.</p>"
            "<p>If you were working on this date, please regularize your attendance or contact HR.</p>"
            "<p>Regards,<br>HR Team</p>"
        ).format(employee.employee_name or employee.name, formatted_date),
        reference_doctype="Employee",
        reference_name=employee.name,
        sender=get_hr_sender(),
    )
