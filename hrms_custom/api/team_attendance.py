import frappe
from frappe import _
from datetime import datetime, date, timedelta
from frappe.utils import getdate, nowdate, today
from hrms_custom.hrms_custom.report.consolidated_attendance_sheet.consolidated_attendance_sheet import (
    _get_downward_chain,
)


def _format_duration(total_seconds):
    if total_seconds < 0:
        total_seconds = 0
    total_minutes = int(total_seconds // 60)
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def _format_time_str(t):
    if isinstance(t, timedelta):
        total_seconds = int(t.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        dt = datetime(2000, 1, 1, hours, minutes)
        return dt.strftime("%I:%M %p")
    elif isinstance(t, datetime):
        return t.strftime("%I:%M %p")
    elif hasattr(t, "strftime"):
        return t.strftime("%I:%M %p")
    return str(t)


@frappe.whitelist()
def is_team_manager():
    """Check if the currently logged-in user manages at least one employee in their downline."""
    user = frappe.session.user
    if not user or user == "Guest":
        return False

    emp_name = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if not emp_name:
        emp_name = frappe.db.get_value("Employee", {"user_id": user}, "name")

    if not emp_name:
        return False

    downline = _get_downward_chain(emp_name)
    return bool(len(downline) > 0)


@frappe.whitelist()
def get_team_attendance_status(date=None):
    """
    Get attendance status for all employees in the calling manager's downline for a given date.
    Results are classified into exactly 3 buckets:
      1. On Time: Present, check-in at or before shift start time
      2. Late In: Present, check-in after shift start time (with late-by duration & check-in time)
      3. Not Yet In: only meaningful for today; no check-in yet, not on leave/WFH/WO/Holiday

    Employees on approved leave, WFH, Week Off, or Holiday, or who otherwise do not fit these
    3 buckets (e.g. absent on past dates with no checkin), are excluded from the returned list.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    # 1. Resolve manager employee
    manager_emp = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "company"],
        as_dict=True,
    )
    if not manager_emp:
        manager_emp = frappe.db.get_value(
            "Employee",
            {"user_id": user},
            ["name", "employee_name", "company"],
            as_dict=True,
        )

    if not manager_emp:
        return {
            "is_manager": False,
            "date": str(getdate(date) if date else getdate(today())),
            "is_today": (getdate(date) if date else getdate(today())) == getdate(today()),
            "message": _("No employee record associated with current user."),
            "counts": {"not_yet_in": 0, "late_in": 0, "on_time": 0, "total": 0},
            "employees": [],
        }

    # 2. Downline resolution using identical hierarchy logic as consolidated attendance sheet
    downline_emp_ids = _get_downward_chain(manager_emp.name)
    if not downline_emp_ids:
        return {
            "is_manager": False,
            "date": str(getdate(date) if date else getdate(today())),
            "is_today": (getdate(date) if date else getdate(today())) == getdate(today()),
            "message": _("No direct or indirect reports found for this manager."),
            "counts": {"not_yet_in": 0, "late_in": 0, "on_time": 0, "total": 0},
            "employees": [],
        }

    target_date = getdate(date) if date else getdate(today())
    is_today = target_date == getdate(today())

    # 3. Fetch downline employees basic info
    employees = frappe.get_all(
        "Employee",
        filters={"name": ["in", list(downline_emp_ids)], "status": "Active"},
        fields=[
            "name",
            "employee_name",
            "image",
            "company",
            "default_shift",
            "holiday_list",
            "date_of_joining",
            "relieving_date",
        ],
        order_by="employee_name asc",
    )

    company_default_holidays = {}

    # 4. Pre-fetch shifts active on target_date
    shift_assignments = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": ["in", list(downline_emp_ids)],
            "docstatus": 1,
            "status": "Active",
            "start_date": ["<=", target_date],
        },
        fields=["employee", "shift_type", "start_date", "end_date"],
        order_by="start_date desc",
    )
    emp_shift_map = {}
    for sa in shift_assignments:
        if sa.employee not in emp_shift_map:
            if not sa.end_date or getdate(sa.end_date) >= target_date:
                emp_shift_map[sa.employee] = sa.shift_type

    # Cache Shift Types
    all_shift_types = frappe.get_all("Shift Type", fields=["name", "start_time", "end_time"])
    shift_type_map = {st.name: st for st in all_shift_types}

    # 5. Pre-fetch checkins on target_date
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", list(downline_emp_ids)],
            "time": ["between", [start_dt, end_dt]],
        },
        fields=["name", "employee", "log_type", "time", "shift", "shift_start"],
        order_by="time asc",
    )
    emp_checkins_map = {}
    for c in checkins:
        emp_checkins_map.setdefault(c.employee, []).append(c)

    # 6. Pre-fetch Attendances on target_date
    attendances = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", list(downline_emp_ids)],
            "attendance_date": target_date,
            "docstatus": 1,
        },
        fields=["name", "employee", "status", "leave_type", "shift", "in_time", "late_entry"],
    )
    emp_attendance_map = {att.employee: att for att in attendances}

    # 7. Pre-fetch approved Leave Applications covering target_date
    leave_apps = frappe.get_all(
        "Leave Application",
        filters={
            "employee": ["in", list(downline_emp_ids)],
            "docstatus": 1,
            "status": "Approved",
            "from_date": ["<=", target_date],
            "to_date": [">=", target_date],
        },
        fields=["employee", "leave_type", "half_day"],
    )
    approved_leave_emps = {la.employee for la in leave_apps}

    # 8. Pre-fetch approved Attendance Requests (WFH)
    wfh_requests = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": ["in", list(downline_emp_ids)],
            "docstatus": 1,
            "reason": ["in", ["Work From Home", "WFH"]],
            "from_date": ["<=", target_date],
            "to_date": [">=", target_date],
        },
        pluck="employee",
    )
    wfh_emps = set(wfh_requests)

    # 9. Classify each employee
    result_employees = []

    for emp in employees:
        emp_id = emp.name

        # Skip if not yet joined or already relieved
        if emp.date_of_joining and getdate(emp.date_of_joining) > target_date:
            continue
        if emp.relieving_date and getdate(emp.relieving_date) < target_date:
            continue

        # Exclusion: Approved leave
        if emp_id in approved_leave_emps:
            continue

        # Exclusion: WFH request
        if emp_id in wfh_emps:
            continue

        # Exclusion: Attendance record marked Leave or WFH
        att_record = emp_attendance_map.get(emp_id)
        if att_record and att_record.status in ("On Leave", "Work From Home"):
            continue

        # Resolve Shift and Shift Start
        shift_name = emp_shift_map.get(emp_id) or emp.default_shift or "GENERAL SHIFT"
        st_obj = shift_type_map.get(shift_name)
        start_time_delta = st_obj.start_time if (st_obj and st_obj.start_time) else timedelta(hours=9)
        expected_start_dt = datetime.combine(target_date, datetime.min.time()) + start_time_delta
        expected_time_str = _format_time_str(start_time_delta)

        # Check for Checkins
        emp_ckins = emp_checkins_map.get(emp_id, [])
        first_in = None
        for ck in emp_ckins:
            if ck.log_type == "IN":
                first_in = ck
                break
        if not first_in and emp_ckins:
            first_in = emp_ckins[0]

        # Case A: Checkin exists -> On Time or Late In
        if first_in:
            checkin_time = first_in.time
            shift_start_dt = first_in.shift_start or expected_start_dt
            checkin_time_str = _format_time_str(checkin_time)

            if checkin_time <= shift_start_dt:
                result_employees.append({
                    "employee": emp_id,
                    "employee_name": emp.employee_name,
                    "image": emp.image or None,
                    "category": "On Time",
                    "time_detail": f"Checked in: {checkin_time_str}",
                    "checkin_time": checkin_time_str,
                    "expected_time": expected_time_str,
                    "late_by": "",
                })
            else:
                diff_sec = (checkin_time - shift_start_dt).total_seconds()
                late_dur = _format_duration(diff_sec)
                result_employees.append({
                    "employee": emp_id,
                    "employee_name": emp.employee_name,
                    "image": emp.image or None,
                    "category": "Late In",
                    "time_detail": f"Late by {late_dur} ({checkin_time_str})",
                    "checkin_time": checkin_time_str,
                    "expected_time": expected_time_str,
                    "late_by": late_dur,
                })
            continue

        # Case B: Attendance record Present with in_time
        if att_record and att_record.status == "Present" and att_record.in_time:
            raw_in = att_record.in_time
            if isinstance(raw_in, timedelta):
                checkin_dt = datetime.combine(target_date, datetime.min.time()) + raw_in
            elif isinstance(raw_in, datetime):
                checkin_dt = raw_in
            else:
                checkin_dt = expected_start_dt

            checkin_time_str = _format_time_str(checkin_dt)
            if checkin_dt <= expected_start_dt:
                result_employees.append({
                    "employee": emp_id,
                    "employee_name": emp.employee_name,
                    "image": emp.image or None,
                    "category": "On Time",
                    "time_detail": f"Checked in: {checkin_time_str}",
                    "checkin_time": checkin_time_str,
                    "expected_time": expected_time_str,
                    "late_by": "",
                })
            else:
                diff_sec = (checkin_dt - expected_start_dt).total_seconds()
                late_dur = _format_duration(diff_sec)
                result_employees.append({
                    "employee": emp_id,
                    "employee_name": emp.employee_name,
                    "image": emp.image or None,
                    "category": "Late In",
                    "time_detail": f"Late by {late_dur} ({checkin_time_str})",
                    "checkin_time": checkin_time_str,
                    "expected_time": expected_time_str,
                    "late_by": late_dur,
                })
            continue

        # Case C: No check-in logged
        # Not Yet In is only applicable when target_date is today
        if not is_today:
            # Past date with no checkin -> excluded
            continue

        # Check Weekly Off and Holiday
        hlist = emp.holiday_list
        if not hlist and emp.company:
            if emp.company not in company_default_holidays:
                company_default_holidays[emp.company] = frappe.db.get_value(
                    "Company", emp.company, "default_holiday_list"
                )
            hlist = company_default_holidays[emp.company]

        is_holiday_or_wo = False
        if hlist:
            hol = frappe.db.get_value(
                "Holiday",
                {"parent": hlist, "holiday_date": target_date},
                ["name", "weekly_off"],
                as_dict=True,
            )
            if hol:
                is_holiday_or_wo = True

        if is_holiday_or_wo:
            continue

        # Not Yet In
        result_employees.append({
            "employee": emp_id,
            "employee_name": emp.employee_name,
            "image": emp.image or None,
            "category": "Not Yet In",
            "time_detail": expected_time_str,
            "checkin_time": "",
            "expected_time": expected_time_str,
            "late_by": "",
        })

    # Summary counts
    counts = {
        "not_yet_in": sum(1 for e in result_employees if e["category"] == "Not Yet In"),
        "late_in": sum(1 for e in result_employees if e["category"] == "Late In"),
        "on_time": sum(1 for e in result_employees if e["category"] == "On Time"),
    }
    counts["total"] = len(result_employees)

    return {
        "is_manager": True,
        "date": str(target_date),
        "is_today": is_today,
        "counts": counts,
        "employees": result_employees,
    }
