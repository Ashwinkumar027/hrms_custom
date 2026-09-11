# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate
from hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet import execute as stock_execute

LEAVE_TYPE_MAP = {
    "casual leave": "CL",
    "comp-off": "CO",
    "compensatory off": "CO",
    "sick leave": "SL",
    "restricted holiday": "RH",
    "earned leave": "EL",
    "privilege leave": "EL",
    "probation casual leave": "PCL",
    "probation leave": "PCL",
    "paternity leave": "PL",
    "maternity leave": "ML",
    "loss of pay": "LOP",
    "leave without pay": "LOP",
    "leave with pay": "LWP",
}

REQUEST_REASON_MAP = {
    "regularization": "REG",
    "on duty": "OD",
    "work from home": "WFH",
    "week off credit": "WOC",
    "late in": "PER/LI",
    "early out": "PER/EO",
}


def execute(filters=None):
    filters = filters or frappe._dict()

    if not filters.get("filter_based_on"):
        if filters.get("month") and filters.get("year"):
            filters.filter_based_on = "Month"
        elif filters.get("start_date") and filters.get("end_date"):
            filters.filter_based_on = "Date Range"
        else:
            filters.filter_based_on = "Date Range" 

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
                "Consolidated Attendance Sheet: skipped company {0} due to error".format(company)
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

    # Detailed View: Enrich cells with custom leave codes, attendance request codes, permissions, and pending markers
    if not filters.get("summarized_view") and data and columns:
        data = _enrich_attendance_grid(data, columns, filters)
        message = _get_legend_message()

    return columns, data, message, chart


def _enrich_attendance_grid(data, columns, filters):
    date_cols = [
        col["fieldname"] for col in columns
        if col.get("fieldname") and _is_date_field(col["fieldname"])
    ]
    if not date_cols or not data:
        return data

    parsed_dates = [datetime.strptime(col, "%d-%m-%Y").date() for col in date_cols]
    start_date = min(parsed_dates)
    end_date = max(parsed_dates)

    employee_ids = list({row["employee"] for row in data if row.get("employee")})
    if not employee_ids:
        return data

    # 1. Fetch Attendance records
    att_records = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", employee_ids],
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1,
        },
        fields=[
            "name",
            "employee",
            "attendance_date",
            "shift",
            "status",
            "leave_type",
            "half_day_status",
            "custom_permission_type",
            "custom_permission_regularized",
            "custom_absent_due_to_missing_checkout",
            "custom_attendance_request",
            "attendance_request",
            "working_hours",
        ],
    )

    # 2. Check for auto-closed OUT checkins
    att_names = [a.name for a in att_records]
    auto_closed_att_names = set()
    if att_names:
        auto_closed_att_names = set(
            frappe.get_all(
                "Employee Checkin",
                filters={
                    "attendance": ["in", att_names],
                    "log_type": "OUT",
                    "custom_auto_closed": 1,
                },
                pluck="attendance",
            )
        )

    # 3. Fetch Leave Applications (approved docstatus=1 and pending docstatus=0)
    leave_applications = frappe.get_all(
        "Leave Application",
        filters={
            "employee": ["in", employee_ids],
            "docstatus": ["in", [0, 1]],
            "status": ["in", ["Open", "Applied", "Approved"]],
            "from_date": ["<=", end_date],
            "to_date": [">=", start_date],
        },
        fields=[
            "name",
            "employee",
            "leave_type",
            "from_date",
            "to_date",
            "half_day",
            "half_day_date",
            "docstatus",
            "status",
        ],
    )

    # 4. Fetch Attendance Requests (approved docstatus=1 and pending docstatus=0)
    att_requests = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": ["in", employee_ids],
            "docstatus": ["in", [0, 1]],
            "from_date": ["<=", end_date],
            "to_date": [">=", start_date],
        },
        fields=[
            "name",
            "employee",
            "reason",
            "from_date",
            "to_date",
            "half_day",
            "half_day_date",
            "docstatus",
        ],
    )

    # Build lookup maps
    # pending_leaves: (employee, date) -> code (e.g. 'CL-PND')
    pending_leaves = {}
    approved_leaves = {}
    for la in leave_applications:
        l_type = (la.leave_type or "").strip().lower()
        l_code = LEAVE_TYPE_MAP.get(l_type, (la.leave_type or "L").strip().upper())
        curr = max(getdate(la.from_date), start_date)
        last = min(getdate(la.to_date), end_date)

        while curr <= last:
            is_half = bool(la.half_day and (not la.half_day_date or getdate(la.half_day_date) == curr))
            if la.docstatus == 0:
                pending_leaves[(la.employee, curr)] = f"HD/{l_code}-PND" if is_half else f"{l_code}-PND"
            elif la.docstatus == 1:
                approved_leaves[(la.employee, curr)] = f"HD/{l_code}" if is_half else l_code
            curr += timedelta(days=1)

    # pending_requests: (employee, date) -> code (e.g. 'REG-PND', 'OD-PND', 'PER/LI-PND', 'WOC-PND')
    # approved_requests: (employee, date) -> code (e.g. 'REG', 'OD', 'WOC', 'WFH')
    pending_requests = {}
    approved_requests = {}
    for ar in att_requests:
        r_reason = (ar.reason or "").strip().lower()
        r_code = REQUEST_REASON_MAP.get(r_reason, (ar.reason or "").strip().upper())
        if not r_code:
            continue
        curr = max(getdate(ar.from_date), start_date)
        last = min(getdate(ar.to_date), end_date)

        while curr <= last:
            if ar.docstatus == 0:
                pending_requests[(ar.employee, curr)] = f"{r_code}-PND"
            elif ar.docstatus == 1:
                approved_requests[(ar.employee, curr)] = r_code
            curr += timedelta(days=1)

    # Map attendance by (employee, shift, date) and (employee, date)
    att_by_shift = {}
    att_by_emp = {}
    for att in att_records:
        shift_key = (att.shift or "").strip()
        att_by_shift[(att.employee, shift_key, att.attendance_date)] = att
        att_by_emp[(att.employee, att.attendance_date)] = att

    # Populate cells
    for row in data:
        emp = row.get("employee")
        if not emp:
            continue
        row_shift = (row.get("shift") or "").strip()

        for d_col, d_obj in zip(date_cols, parsed_dates):
            stock_val = row.get(d_col)
            row[d_col] = _resolve_cell_status(
                emp=emp,
                date_obj=d_obj,
                row_shift=row_shift,
                stock_val=stock_val,
                pending_leaves=pending_leaves,
                pending_requests=pending_requests,
                approved_leaves=approved_leaves,
                approved_requests=approved_requests,
                att_by_shift=att_by_shift,
                att_by_emp=att_by_emp,
                auto_closed_att_names=auto_closed_att_names,
            )

    return data


def _resolve_cell_status(
    emp,
    date_obj,
    row_shift,
    stock_val,
    pending_leaves,
    pending_requests,
    approved_leaves,
    approved_requests,
    att_by_shift,
    att_by_emp,
    auto_closed_att_names,
):
    # 1. Pending Leaves take highest visibility
    if (emp, date_obj) in pending_leaves:
        return pending_leaves[(emp, date_obj)]

    # 2. Pending Attendance Requests
    if (emp, date_obj) in pending_requests:
        return pending_requests[(emp, date_obj)]

    # Match Attendance record (shift-specific first, then general)
    att = att_by_shift.get((emp, row_shift, date_obj)) or att_by_emp.get((emp, date_obj))

    # 3. Approved Leave
    if (emp, date_obj) in approved_leaves:
        return approved_leaves[(emp, date_obj)]
    if att and (att.status == "On Leave" or att.leave_type):
        l_type = (att.leave_type or "").strip().lower()
        return LEAVE_TYPE_MAP.get(l_type, (att.leave_type or "L").strip().upper())

    # 4. Approved Attendance Request (Regularization, On Duty, Week Off Credit, WFH)
    if (emp, date_obj) in approved_requests:
        return approved_requests[(emp, date_obj)]
    if att and (att.custom_attendance_request or att.attendance_request):
        req_name = att.custom_attendance_request or att.attendance_request
        req_reason = frappe.db.get_value("Attendance Request", req_name, "reason")
        if req_reason:
            r_code = REQUEST_REASON_MAP.get(req_reason.strip().lower())
            if r_code:
                return r_code

    # 5. Permission on Attendance
    if att and cint(att.custom_permission_regularized) == 1:
        p_type = (att.custom_permission_type or "").strip().lower()
        if p_type == "late in":
            return "PER/LI"
        elif p_type == "early out":
            return "PER/EO"

    # 6. Missing Checkout / Auto-closed
    if att and (cint(att.custom_absent_due_to_missing_checkout) == 1 or att.name in auto_closed_att_names):
        return "M(CO)"

    # 7. Half Day
    if att and att.status == "Half Day":
        half_present = (
            att.half_day_status == "Present"
            or (att.half_day_status is None and flt(att.working_hours) > 0)
        )
        if att.leave_type:
            l_code = LEAVE_TYPE_MAP.get(att.leave_type.strip().lower(), "L")
            return f"HD/{l_code}" if half_present else "HD/A"
        return "HD/P" if half_present else "HD/A"

    # 8. Standard Attendance Record Status
    if att:
        if att.status == "Work From Home":
            return "WFH"
        elif att.status == "Present":
            return "P"
        elif att.status == "Absent":
            return "A"

    # 9. Fallback to existing stock value (which preserves WO, H, or blank before DOJ)
    return stock_val or ""


def _is_date_field(val):
    if not isinstance(val, str) or len(val) != 10:
        return False
    parts = val.split("-")
    return len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit()


def _get_legend_message():
    sections = [
        (
            "Attendance",
            [
                ("Present", "P", "#27ae60"),
                ("Absent", "A", "#e74c3c"),
                ("Work From Home", "WFH", "#16a085"),
                ("Half Day Present", "HD/P", "#9b59b6"),
                ("Half Day Absent", "HD/A", "#e67e22"),
                ("Weekly Off", "WO", "#7f8c8d"),
                ("Holiday", "H", "#7f8c8d"),
            ],
        ),
        (
            "Approved Leaves",
            [
                ("Casual Leave", "CL", "#2980b9"),
                ("Comp-Off", "CO", "#2980b9"),
                ("Sick Leave", "SL", "#2980b9"),
                ("Restricted Holiday", "RH", "#2980b9"),
                ("Earned Leave", "EL", "#2980b9"),
                ("Probation Casual Leave", "PCL", "#2980b9"),
                ("Paternity leave", "PL", "#2980b9"),
                ("Maternity Leave", "ML", "#2980b9"),
                ("Loss Of Pay", "LOP", "#e74c3c"),
                ("Leave With Pay", "LWP", "#2980b9"),
            ],
        ),
        (
            "Requests & Permissions",
            [
                ("Regularization", "REG", "#16a085"),
                ("On Duty", "OD", "#16a085"),
                ("Week Off Credit", "WOC", "#16a085"),
                ("Late In Permission", "PER/LI", "#8e44ad"),
                ("Early Out Permission", "PER/EO", "#8e44ad"),
                ("Missing Checkout / Auto-Closed", "M(CO)", "#e74c3c"),
            ],
        ),
        (
            "Pending Approvals",
            [
                ("Pending Requests", "*-PND (e.g. CL-PND, REG-PND, OD-PND, PER/LI-PND, WOC-PND)", "#e74c3c"),
            ],
        ),
    ]

    message = "<div style='font-size: 12px; line-height: 24px; padding: 6px 0;'>"
    for title, items in sections:
        message += f"<div style='margin-bottom: 4px;'><strong style='color: #2c3e50;'>{title}:</strong> "
        for label, code, color in items:
            message += f"""
                <span style='border-left: 3px solid {color}; padding: 1px 8px 1px 5px; margin: 0 4px; display: inline-block;'>
                    {label} - <b>{code}</b>
                </span>
            """
        message += "</div>"
    message += "</div>"
    return message


def _get_downward_chain(manager):
    """BFS through Employee.reports_to to find all employees under `manager`,
    at any depth, including the manager' direct and indirect reports."""
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
