import frappe
from frappe.utils import getdate
from hrms_custom.hrms_custom.report.consolidated_attendance_sheet.consolidated_attendance_sheet import (
    _get_downward_chain,
)


def execute(filters=None):
    filters = filters or frappe._dict()
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": "Date", "fieldname": "log_date", "fieldtype": "Date", "width": 100},
        {"label": "Check In", "fieldname": "check_in", "fieldtype": "Data", "width": 100},
        {"label": "Check Out", "fieldname": "check_out", "fieldtype": "Data", "width": 100},
        {"label": "Check-in latitude and longitude", "fieldname": "check_in_lat_long", "fieldtype": "Data", "width": 180},
        {"label": "Check-out latitude and longitude", "fieldname": "check_out_lat_long", "fieldtype": "Data", "width": 180},
        {"label": "Auto Checkout", "fieldname": "auto_closed", "fieldtype": "Data", "width": 120},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 130},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 140},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
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
    for (employee, log_date), day_logs in sorted(grouped.items(), key=lambda x: (x[0][1], x[0][0])):
        emp = employee_map.get(employee)
        if not emp:
            continue

        ins = [l for l in day_logs if l.log_type == "IN"]
        outs = [l for l in day_logs if l.log_type == "OUT"]

        first_in = ins[0] if ins else None
        last_out = outs[-1] if outs else None

        auto_closed = ""
        if last_out and last_out.custom_auto_closed:
            auto_closed = "AUTO"

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
            "check_in_lat_long": _format_lat_long(first_in),
            "check_out_lat_long": _format_lat_long(last_out),
            "auto_closed": auto_closed,
            "shift": shift,
            "location": location,
            "company": emp.company,
            "department": emp.department,
            "branch": emp.branch,
        })

    return data
