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

    # Mute popups like 'No attendance records found.' when looping through empty companies
    saved_mute = getattr(frappe.flags, "mute_messages", False)
    frappe.flags.mute_messages = True
    try:
        for company in companies:
            run_filters = frappe._dict(filters)
            run_filters.company = company
            try:
                c, d, m, ch = stock_execute(run_filters)
            except Exception:
                frappe.logger("hrms_custom").warning(
                    f"Consolidated Attendance Sheet: skipped company {company} due to error"
                )
                continue
            if c and columns is None:
                columns = c
            if ch and chart is None:
                chart = ch
            if d:
                all_data.extend(d)
    finally:
        frappe.flags.mute_messages = saved_mute

    data = all_data

    if reports_to:
        allowed_employees = _get_downward_chain(reports_to)
        data = [
            row for row in data
            if row.get("employee") in allowed_employees
        ]

    # Widen date columns to 80px & center align to prevent badge truncation (e.g. REG-PND)
    if columns:
        for col in columns:
            if col.get("fieldname") and _is_date_field(col["fieldname"]):
                col["width"] = 80
                col["align"] = "center"

    # Detailed View: Enrich cells with custom leave codes, attendance request codes, permissions, and pending markers
    if not filters.get("summarized_view") and data and columns:
        data = _enrich_attendance_grid(data, columns, filters)
        # Suppress heavy chart in detailed view so KPIs and grid are immediately visible at the top
        chart = None
        kpi_html = _get_kpi_summary_html(data, columns)
        legend_html = _get_legend_message()
        message = f"{kpi_html}{legend_html}"

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


def _get_kpi_summary_html(data, columns):
    """Generate 4 executive KPI summary cards above the grid."""
    date_cols = [
        col["fieldname"] for col in columns
        if col.get("fieldname") and _is_date_field(col["fieldname"])
    ]
    employees = {r.get("employee") for r in data if r.get("employee")}
    total_emp = len(employees)

    present_count = 0
    absent_count = 0
    pending_count = 0

    for row in data:
        if not row.get("employee"):
            continue
        for d_col in date_cols:
            val = str(row.get(d_col) or "").strip()
            if not val:
                continue
            if val.endswith("-PND"):
                pending_count += 1
            if val in ("P", "WFH", "REG", "OD", "WOC") or val.startswith("PER/"):
                present_count += 1
            elif val.startswith("HD/P"):
                present_count += 0.5
                absent_count += 0.5
            elif val in ("A", "LOP", "M(CO)") or val.startswith("HD/A"):
                absent_count += 1

    denominator = present_count + absent_count
    att_rate = (present_count / denominator * 100.0) if denominator > 0 else 0.0

    cards_html = f"""
    <div style="display: flex; gap: 14px; margin-bottom: 12px; flex-wrap: wrap; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #3b82f6;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Active Headcount</div>
            <div style="font-size: 22px; font-weight: 700; color: #1e293b; margin-top: 2px;">{total_emp} <span style="font-size: 12px; font-weight: 500; color: #94a3b8;">Employees</span></div>
        </div>
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #10b981;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Attendance Rate</div>
            <div style="font-size: 22px; font-weight: 700; color: #0f766e; margin-top: 2px;">{att_rate:.1f}%</div>
        </div>
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #e74c3c;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Absences / LOP / M(CO)</div>
            <div style="font-size: 22px; font-weight: 700; color: #e74c3c; margin-top: 2px;">{int(absent_count)} <span style="font-size: 12px; font-weight: 500; color: #94a3b8;">Days</span></div>
        </div>
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #f59e0b;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Pending Approvals</div>
            <div style="font-size: 22px; font-weight: 700; color: #b45309; margin-top: 2px;">{pending_count} <span style="font-size: 12px; font-weight: 500; color: #94a3b8;">Requests</span></div>
        </div>
    </div>
    """
    return cards_html


def _get_legend_message():
    sections = [
        (
            "Attendance",
            [
                ("Present", "P", "color: #15803d; font-weight: 700;"),
                ("Absent", "A", "color: #dc2626; font-weight: 800;"),
                ("Work From Home", "WFH", "color: #15803d; font-weight: 700;"),
                ("Half Day Present", "HD/P", "color: #7c3aed; background: #faf5ff; border: 1px solid #f3e8ff; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Half Day Absent", "HD/A", "color: #c2410c; background: #fff7ed; border: 1px solid #ffedd5; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Weekly Off", "WO", "color: #94a3b8; font-weight: 600;"),
                ("Holiday", "H", "color: #94a3b8; font-weight: 600;"),
            ],
        ),
        (
            "Approved Leaves",
            [
                ("Casual Leave", "CL", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Comp-Off", "CO", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Sick Leave", "SL", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Restricted Holiday", "RH", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Earned Leave", "EL", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Probation Casual Leave", "PCL", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Paternity Leave", "PL", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Maternity Leave", "ML", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Loss Of Pay", "LOP", "color: #ffffff; background: #e74c3c; border: 1px solid #c0392b; padding: 2px 5px; border-radius: 4px; font-weight: 700;"),
                ("Leave With Pay", "LWP", "color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
            ],
        ),
        (
            "Requests & Permissions",
            [
                ("Regularization", "REG", "color: #0f766e; background: #f0fdfa; border: 1px solid #99f6e4; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("On Duty", "OD", "color: #0f766e; background: #f0fdfa; border: 1px solid #99f6e4; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Week Off Credit", "WOC", "color: #0f766e; background: #f0fdfa; border: 1px solid #99f6e4; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Late In Permission", "PER/LI", "color: #6d28d9; background: #f5f3ff; border: 1px solid #ddd6fe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Early Out Permission", "PER/EO", "color: #6d28d9; background: #f5f3ff; border: 1px solid #ddd6fe; padding: 2px 5px; border-radius: 4px; font-weight: 600;"),
                ("Missing Checkout / Auto-Closed", "M(CO)", "color: #ffffff; background: #e74c3c; border: 1px solid #c0392b; padding: 2px 5px; border-radius: 4px; font-weight: 700;"),
            ],
        ),
        (
            "Pending Approvals",
            [
                ("Pending Requests", "*-PND (e.g. CL-PND, REG-PND, OD-PND, PER/LI-PND, WOC-PND)", "color: #e74c3c; background: #fff5f5; border: 1px dashed #e74c3c; padding: 2px 5px; border-radius: 4px; font-weight: 700;"),
            ],
        ),
    ]

    details_html = """
    <details style="margin-bottom: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11.5px;">
        <summary style="font-weight: 600; color: #475569; cursor: pointer; user-select: none; outline: none; padding: 2px 0;">
            Attendance Legend & Leave Codes
            <span style="font-weight: 400; color: #94a3b8; font-size: 11px; margin-left: 8px;">(Click to expand / collapse)</span>
        </summary>
        <div style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px;">
    """

    for title, items in sections:
        details_html += f"""
            <div style="display: flex; align-items: baseline; flex-wrap: wrap; gap: 6px;">
                <span style="font-weight: 600; color: #334155; min-width: 145px;">{title}:</span>
        """
        for label, code, style_str in items:
            details_html += f"""
                <span style="display: inline-flex; align-items: center; gap: 4px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 4px; padding: 2px 6px; margin: 1px 2px;">
                    <span style="color: #64748b; font-size: 11px;">{label}</span>
                    <span style="{style_str} font-size: 10.5px;">{code}</span>
                </span>
            """
        details_html += "</div>"

    details_html += """
        </div>
    </details>
    """
    return details_html


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
