import frappe
from hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet import execute as stock_execute


def execute(filters=None):
    filters = filters or frappe._dict()

    reports_to = filters.pop("reports_to", None)

    if filters.get("company"):
        companies = [filters.company]
    else:
        companies = frappe.get_all("Company", pluck="name")

    all_data = []
    columns = None
    chart = None
    message = None

    for company in companies:
        run_filters = frappe._dict(filters)
        run_filters.company = company
        try:
            c, d, m, ch = stock_execute(run_filters)
        except Exception:
            frappe.logger("hrms_custom").warning(
                "Monthly Attendance Sheet Custom: skipped company {0} due to error".format(company)
            )
            continue
        if c and columns is None:
            columns = c
        if ch and chart is None:
            chart = ch
        if m and message is None:
            message = m
        if d:
            all_data.extend(d)

    data = all_data

    if reports_to:
        allowed_employees = _get_downward_chain(reports_to)
        data = [
            row for row in data
            if row.get("employee") in allowed_employees
        ]

    return columns, data, message, chart


def _get_downward_chain(manager):
    """BFS through Employee.reports_to to find all employees under `manager`,
    at any depth, including the manager'direct and indirect reports."""
    result = set()
    frontier = [manager]

    while frontier:
        children = frappe.get_all(
            "Employee",
            filters={"reports_to": ["in", frontier], "status": "Active"},
            pluck="name",
        )
        new_children = [c for c in children if c not in result]
        result.update(new_children)
        frontier = new_children

    return result
