import frappe
from frappe.utils import add_days, today, getdate


def send_upcoming_holiday_notifications():
    """Daily scheduler: notify all employees of a company a day before
    a National Holiday (company's default Holiday List) or
    Optional Holiday (active Leave Period's Holiday List for Optional Leave)."""

    if not frappe.conf.get("enable_upcoming_holiday_email"):
        return

    tomorrow = getdate(add_days(today(), 1))

    companies = frappe.get_all(
        "Company", fields=["name", "default_holiday_list"]
    )

    for company in companies:
        holiday_name = None
        holiday_type = None

        # 1. National Holiday - company's default Holiday List, excluding weekly off
        if company.default_holiday_list:
            holiday_name = frappe.db.get_value(
                "Holiday",
                {
                    "parent": company.default_holiday_list,
                    "holiday_date": tomorrow,
                    "weekly_off": 0,
                },
                "description",
            )
            if holiday_name:
                holiday_name = frappe.utils.strip_html(holiday_name).strip()
                holiday_type = "National Holiday"

        # 2. Optional Holiday - active Leave Period's Holiday List for Optional Leave
        if not holiday_name:
            optional_holiday_list = frappe.db.get_value(
                "Leave Period",
                {"company": company.name, "is_active": 1},
                "optional_holiday_list",
            )
            if optional_holiday_list:
                holiday_name = frappe.db.get_value(
                    "Holiday",
                    {
                        "parent": optional_holiday_list,
                        "holiday_date": tomorrow,
                    },
                    "description",
                )
                if holiday_name:
                    holiday_name = frappe.utils.strip_html(holiday_name).strip()
                    holiday_type = "Optional Holiday"

        if not holiday_name:
            continue

        # 3. Collect active employees of this company
        employees = frappe.get_all(
            "Employee",
            filters={"company": company.name, "status": "Active"},
            fields=["user_id", "company_email", "personal_email"],
        )

        bcc_list = []
        for emp in employees:
            email = emp.user_id or emp.company_email or emp.personal_email
            if email and frappe.utils.validate_email_address(email, throw=False):
                bcc_list.append(email)

        if not bcc_list:
            continue

        subject = f"Reminder: {holiday_type} Tomorrow - {holiday_name}"
        message = f"""
        <p>Dear Team,</p>
        <p>This is a reminder that <b>{tomorrow.strftime('%d-%m-%Y')}</b> is a
        <b>{holiday_type}</b> on account of <b>{holiday_name}</b>.</p>
        <p>Regards,<br>HR Team</p>
        """

        frappe.sendmail(
            recipients=["kishore.k@aionioncapital.com"],
            bcc=bcc_list,
            subject=subject,
            message=message,
            now=True,
        )
