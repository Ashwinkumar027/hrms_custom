import frappe
from frappe import _
from frappe.utils import getdate
from hrms_custom.hrms_custom.report.consolidated_attendance_sheet.consolidated_attendance_sheet import (
    _get_downward_chain,
)


def execute(filters=None):
    filters = filters or frappe._dict()
    columns = get_columns()
    data = get_data(filters)
    message = _get_kpi_summary_html(data)
    return columns, data, message, None


def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": _("Date"), "fieldname": "log_date", "fieldtype": "Date", "width": 115, "align": "center"},
        {"label": _("Check In"), "fieldname": "check_in", "fieldtype": "Data", "width": 95, "align": "center"},
        {"label": _("Check Out"), "fieldname": "check_out", "fieldtype": "Data", "width": 95, "align": "center"},
        {"label": _("Working Hours"), "fieldname": "working_hours", "fieldtype": "Data", "width": 110, "align": "center"},
        {"label": _("Check-in GPS"), "fieldname": "check_in_lat_long", "fieldtype": "Data", "width": 145},
        {"label": _("Check-out GPS"), "fieldname": "check_out_lat_long", "fieldtype": "Data", "width": 145},
        {"label": _("Checkout Type"), "fieldname": "auto_closed", "fieldtype": "Data", "width": 115, "align": "center"},
        {"label": _("Shift"), "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 130},
        {"label": _("Location"), "fieldname": "location", "fieldtype": "Data", "width": 140},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
    ]


def get_employees(filters):
    emp_filters = {"status": "Active"}
    if filters.get("employee"):
        emp_filters["name"] = filters.employee
    if filters.get("company"):
        emp_filters["company"] = filters.company
    if filters.get("department"):
        emp_filters["department"] = filters.department
    if filters.get("branch"):
        emp_filters["branch"] = filters.branch

    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "company", "department", "branch"],
    )

    if filters.get("reports_to"):
        allowed = _get_downward_chain(filters.reports_to)
        employees = [e for e in employees if e.name in allowed]

    return {e.name: e for e in employees}


def _format_lat_long(log):
    if not log:
        return ""
    lat = getattr(log, "latitude", None)
    lon = getattr(log, "longitude", None)

    if isinstance(lat, str):
        lat = lat.strip() or None
    if isinstance(lon, str):
        lon = lon.strip() or None

    lat_val = None
    lon_val = None
    if lat is not None:
        try:
            lat_val = float(lat)
        except (ValueError, TypeError):
            lat_val = None

    if lon is not None:
        try:
            lon_val = float(lon)
        except (ValueError, TypeError):
            lon_val = None

    has_lat = lat_val is not None and lat_val != 0.0
    has_lon = lon_val is not None and lon_val != 0.0

    if has_lat and has_lon:
        return f"{lat}, {lon}"
    elif has_lat:
        return str(lat)
    elif has_lon:
        return str(lon)
    return ""


def get_data(filters):
    start_date = getdate(filters.get("start_date"))
    end_date = getdate(filters.get("end_date"))

    employee_map = get_employees(filters)
    if not employee_map:
        return []

    logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", list(employee_map.keys())],
            "time": ["between", [str(start_date) + " 00:00:00", str(end_date) + " 23:59:59"]],
        },
        fields=[
            "employee",
            "log_type",
            "time",
            "shift",
            "latitude",
            "longitude",
            "custom_auto_closed",
            "custom_validated_shift_location",
        ],
        order_by="employee asc, time asc",
    )

    grouped = {}
    for log in logs:
        key = (log.employee, getdate(log.time))
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(log)

    data = []
    status_filter = filters.get("status")

    for (employee, log_date), day_logs in sorted(grouped.items(), key=lambda x: (x[0][1], x[0][0])):
        emp = employee_map.get(employee)
        if not emp:
            continue

        ins = [l for l in day_logs if l.log_type == "IN"]
        outs = [l for l in day_logs if l.log_type == "OUT"]

        first_in = ins[0] if ins else None
        last_out = outs[-1] if outs else None

        # Determine status
        auto_closed = ""
        if last_out and last_out.custom_auto_closed:
            auto_closed = "AUTO"
            row_status = "Auto Closed"
        elif not first_in:
            row_status = "Missing Check-in"
        elif not last_out:
            row_status = "Missing Check-out"
        else:
            row_status = "Completed"

        # Apply status filter if specified
        if status_filter and row_status != status_filter:
            continue

        # Calculate working hours between first IN and very last OUT
        working_hours = "-"
        if first_in and last_out and last_out.time > first_in.time:
            diff = last_out.time - first_in.time
            total_secs = int(diff.total_seconds())
            hrs = total_secs // 3600
            mins = (total_secs % 3600) // 60
            working_hours = f"{hrs}h {mins:02d}m"

        location = ""
        if first_in and first_in.custom_validated_shift_location:
            location = first_in.custom_validated_shift_location

        shift = ""
        if first_in and first_in.shift:
            shift = first_in.shift
        elif last_out and last_out.shift:
            shift = last_out.shift

        data.append({
            "employee": employee,
            "employee_name": emp.employee_name,
            "log_date": log_date,
            "check_in": first_in.time.strftime("%H:%M") if first_in else "",
            "check_out": last_out.time.strftime("%H:%M") if last_out else "",
            "working_hours": working_hours,
            "check_in_lat_long": _format_lat_long(first_in),
            "check_out_lat_long": _format_lat_long(last_out),
            "auto_closed": auto_closed,
            "status": row_status,
            "shift": shift,
            "location": location,
            "company": emp.company,
            "department": emp.department,
            "branch": emp.branch,
        })

    return data


def _get_kpi_summary_html(data):
    """Generate 4 executive KPI cards for Checkin Summary."""
    total_logs = len(data)
    missing_count = 0
    auto_closed_count = 0
    total_duration_secs = 0
    valid_duration_count = 0

    for r in data:
        status = r.get("status")
        if status in ("Missing Check-out", "Missing Check-in"):
            missing_count += 1
        elif status == "Auto Closed":
            auto_closed_count += 1

        wh = r.get("working_hours", "-")
        if wh and wh != "-" and "h" in wh:
            try:
                parts = wh.split("h")
                hrs = int(parts[0].strip())
                mins = int(parts[1].replace("m", "").strip())
                total_duration_secs += hrs * 3600 + mins * 60
                valid_duration_count += 1
            except Exception:
                pass

    avg_wh = "0.0h"
    if valid_duration_count > 0:
        avg_hrs = (total_duration_secs / valid_duration_count) / 3600.0
        avg_wh = f"{avg_hrs:.1f}h"

    cards_html = f"""
    <div style="display: flex; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #3b82f6;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Total Logged Shifts</div>
            <div style="font-size: 22px; font-weight: 700; color: #1e293b; margin-top: 2px;">{total_logs} <span style="font-size: 12px; font-weight: 500; color: #94a3b8;">Logs</span></div>
        </div>
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #e74c3c;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Missing In / Out</div>
            <div style="font-size: 22px; font-weight: 700; color: #e74c3c; margin-top: 2px;">{missing_count} <span style="font-size: 12px; font-weight: 500; color: #94a3b8;">Anomalies</span></div>
        </div>
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #ea580c;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Auto Closed</div>
            <div style="font-size: 22px; font-weight: 700; color: #ea580c; margin-top: 2px;">{auto_closed_count} <span style="font-size: 12px; font-weight: 500; color: #94a3b8;">Shifts</span></div>
        </div>
        <div style="flex: 1; min-width: 170px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #10b981;">
            <div style="font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Avg. Working Hours</div>
            <div style="font-size: 22px; font-weight: 700; color: #0f766e; margin-top: 2px;">{avg_wh} <span style="font-size: 12px; font-weight: 500; color: #94a3b8;">/ Day</span></div>
        </div>
    </div>
    """
    return cards_html
