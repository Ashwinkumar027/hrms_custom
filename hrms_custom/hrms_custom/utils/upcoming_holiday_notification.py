import frappe
from frappe.utils import add_days, today, getdate


def send_upcoming_holiday_notifications():
    """Daily scheduler: notify employees of each company on their last working day
    before an upcoming National Holiday or Optional/Restricted Holiday.
    Checks Holiday List Assignment for the company, falling back to company defaults."""

    if not frappe.db.get_single_value("HR Settings", "custom_enable_upcoming_holiday_email"):
        return

    today_date = getdate(today())
    companies = frappe.get_all("Company", fields=["name", "default_holiday_list"])

    for company in companies:
        _process_company_upcoming_holidays(company, today_date)


def _process_company_upcoming_holidays(company, today_date):
    national_hl = get_company_holiday_list(company.name, as_on=today_date)
    optional_hl = _get_company_optional_holiday_list(company.name)

    if not national_hl and not optional_hl:
        return

    def is_non_working_day(check_date):
        if national_hl and frappe.db.exists("Holiday", {"parent": national_hl, "holiday_date": check_date}):
            return True
        # Fallback if no holiday list: Sunday is weekly off
        return getdate(check_date).weekday() == 6

    # Inspect upcoming dates within a 4-day window (e.g. Friday notifying for Saturday, Sunday, Monday)
    for days_ahead in range(1, 5):
        h_date = getdate(add_days(today_date, days_ahead))
        h_name = None
        h_type = None

        # 1. National Holiday (company holiday list, excluding weekly off)
        if national_hl:
            desc = frappe.db.get_value(
                "Holiday",
                {
                    "parent": national_hl,
                    "holiday_date": h_date,
                    "weekly_off": 0,
                },
                "description",
            )
            if desc:
                h_name = frappe.utils.strip_html(desc).strip()
                h_type = "National Holiday"

        # 2. Optional Holiday (Leave Period's Holiday List for Optional Leave)
        if not h_name and optional_hl:
            desc = frappe.db.get_value(
                "Holiday",
                {
                    "parent": optional_hl,
                    "holiday_date": h_date,
                },
                "description",
            )
            if desc:
                h_name = frappe.utils.strip_html(desc).strip()
                h_type = "Optional Holiday"

        if not h_name:
            continue

        # 3. Calculate the last working day before this holiday
        curr = add_days(h_date, -1)
        while is_non_working_day(curr):
            curr = add_days(curr, -1)
        last_working_day = getdate(curr)

        # Notify if today is the last working day, OR if today is between the last working day
        # and the holiday (e.g. over the weekend if missed earlier)
        should_notify = (today_date == last_working_day) or (last_working_day < today_date < h_date)
        if not should_notify:
            continue

        # Deduplication check: only notify once per holiday per company
        cache_key = f"holiday_notified:{company.name}:{h_date}:{h_name}"
        if frappe.cache.get_value(cache_key):
            continue

        # 4. Collect active employees of this company
        employees = frappe.get_all(
            "Employee",
            filters={"company": company.name, "status": "Active"},
            fields=["user_id", "company_email", "personal_email"],
        )

        bcc_list = []
        for emp in employees:
            email = emp.user_id or emp.company_email or emp.personal_email
            if email and frappe.utils.validate_email_address(email, throw=False):
                if email not in bcc_list:
                    bcc_list.append(email)

        if not bcc_list:
            continue

        # Format date and subject
        if h_date == add_days(today_date, 1):
            subject = f"Reminder: {h_type} Tomorrow - {h_name}"
            date_text = f"tomorrow, <b>{h_date.strftime('%A, %d-%m-%Y')}</b>"
        else:
            subject = f"Reminder: {h_type} on {h_date.strftime('%A')} ({h_date.strftime('%d-%m-%Y')}) - {h_name}"
            date_text = f"<b>{h_date.strftime('%A, %d-%m-%Y')}</b>"

        message = f"""
        <p>Dear Team,</p>
        <p>This is a reminder that {date_text} is a
        <b>{h_type}</b> on account of <b>{h_name}</b>.</p>
        <p>Regards,<br>HR Team</p>
        """

        frappe.sendmail(
            recipients=["kishore.k@aionioncapital.com"],
            bcc=bcc_list,
            subject=subject,
            message=message,
            now=True,
        )

        frappe.cache.set_value(cache_key, 1, expires_in_sec=86400 * 7)


def get_company_holiday_list(company_name, as_on=None):
    """Resolves the company's active holiday list:
    1. Checks active Holiday List Assignment for the Company where to_date >= as_on.
    2. Falls back to Company.default_holiday_list.
    3. Falls back to any active Holiday List covering as_on."""
    as_on = getdate(as_on or today())

    if frappe.db.exists("DocType", "Holiday List Assignment"):
        HLA = frappe.qb.DocType("Holiday List Assignment")
        HL = frappe.qb.DocType("Holiday List")
        assigned = (
            frappe.qb.from_(HLA)
            .join(HL).on(HLA.holiday_list == HL.name)
            .select(HLA.holiday_list)
            .where(HLA.assigned_to == company_name)
            .where(HLA.docstatus == 1)
            .where(HLA.from_date <= as_on)
            .where(HL.to_date >= as_on)
            .orderby(HLA.from_date, order=frappe.qb.desc)
            .limit(1)
        ).run()
        if assigned and assigned[0][0]:
            return assigned[0][0]

    comp_default = frappe.db.get_value("Company", company_name, "default_holiday_list")
    if comp_default:
        hl_end = frappe.db.get_value("Holiday List", comp_default, "to_date")
        if not hl_end or getdate(hl_end) >= as_on:
            return comp_default

    return frappe.db.get_value(
        "Holiday List",
        {"from_date": ["<=", as_on], "to_date": [">=", as_on]},
        "name",
    )


def _get_company_optional_holiday_list(company_name):
    """Finds the optional holiday list for the company's active Leave Period."""
    optional_hl = frappe.db.get_value(
        "Leave Period",
        {"company": company_name, "is_active": 1},
        "optional_holiday_list",
    )
    if not optional_hl:
        optional_hl = frappe.db.get_value(
            "Leave Period",
            {"company": ["in", [company_name, ""]], "is_active": 1},
            "optional_holiday_list",
        )
    if not optional_hl:
        optional_hl = frappe.db.get_value(
            "Leave Period",
            {"is_active": 1},
            "optional_holiday_list",
        )
    return optional_hl
