# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, getdate


@frappe.whitelist()
def get_checkin_log(employee, date):
    """
    Whitelisted RPC method to fetch check-in / check-out logs for a given employee and date.
    Permissions:
    - User must have read permission on 'Employee Checkin'
    - User must have read permission on the specific 'Employee' record
    """
    if not employee or not frappe.db.exists("Employee", employee):
        frappe.throw(_("Invalid or missing Employee"), frappe.ValidationError)

    try:
        date_obj = getdate(date)
    except Exception:
        frappe.throw(_("Invalid date format"), frappe.ValidationError)

    # Permission checks (respects Frappe & User Permissions without bypass)
    if not frappe.has_permission("Employee Checkin", "read"):
        frappe.throw(_("Not permitted to view Employee Checkin"), frappe.PermissionError)

    if not frappe.has_permission("Employee", "read", employee):
        frappe.throw(_("Not permitted to view records for this employee"), frappe.PermissionError)

    date_str = str(date_obj)

    # Lookup submitted Attendance for (employee, date)
    att = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": date_obj, "docstatus": 1},
        ["name", "status", "attendance_request", "custom_attendance_request"],
        as_dict=True,
    )

    attendance_status = att.status if att else "No Attendance record"
    attendance_request = (att.custom_attendance_request or att.attendance_request) if att else None

    # Fetch logs:
    # 1. Linked to that day's submitted Attendance record (handles night shifts)
    # 2. Within calendar day 00:00:00 to 23:59:59
    logs_by_name = {}

    if att and att.name:
        att_logs = frappe.get_all(
            "Employee Checkin",
            filters={"employee": employee, "attendance": att.name},
            fields=["name", "time", "log_type", "shift", "device_id", "custom_auto_closed"],
            order_by="time asc",
            limit=100,
        )
        for l in att_logs:
            logs_by_name[l.name] = l

    day_logs = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{date_str} 00:00:00", f"{date_str} 23:59:59"]],
        },
        fields=["name", "time", "log_type", "shift", "device_id", "custom_auto_closed"],
        order_by="time asc",
        limit=100,
    )
    for l in day_logs:
        if l.name not in logs_by_name:
            logs_by_name[l.name] = l

    # Sort combined logs by time ascending
    all_logs = sorted(logs_by_name.values(), key=lambda x: x.time)[:100]

    ins = [l for l in all_logs if l.log_type == "IN"]
    outs = [l for l in all_logs if l.log_type == "OUT"]

    first_in = ins[0] if ins else None
    last_out = outs[-1] if outs else None

    # Compute duration if first IN and last OUT exist and last OUT is not auto-closed
    total_duration = None
    if first_in and last_out and not last_out.custom_auto_closed and last_out.time > first_in.time:
        diff = last_out.time - first_in.time
        total_secs = int(diff.total_seconds())
        hrs = total_secs // 3600
        mins = (total_secs % 3600) // 60
        total_duration = f"{hrs}h {mins:02d}m"

    formatted_logs = []
    for l in all_logs:
        note = ""
        if cint(l.custom_auto_closed) and l.log_type == "OUT":
            note = "Auto-closed by system (no real check-out)"

        formatted_logs.append({
            "name": l.name,
            "time": l.time.strftime("%H:%M:%S") if l.time else "",
            "date": l.time.strftime("%d-%m-%Y") if l.time else "",
            "log_type": l.log_type,
            "shift": l.shift or "",
            "device_id": l.device_id or "",
            "auto_closed": cint(l.custom_auto_closed),
            "note": note,
        })

    return {
        "attendance_status": attendance_status,
        "attendance_request": attendance_request,
        "first_in": first_in.time.strftime("%H:%M") if first_in else None,
        "last_out": last_out.time.strftime("%H:%M") if last_out else None,
        "last_out_auto_closed": bool(last_out and last_out.custom_auto_closed),
        "total_duration": total_duration,
        "logs": formatted_logs,
    }
