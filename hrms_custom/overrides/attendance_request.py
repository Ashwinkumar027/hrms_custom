import calendar
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, get_datetime_str, getdate, time_diff_in_hours

from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest


class CustomAttendanceRequest(AttendanceRequest):
    def validate(self):
        self._validate_single_date()
        self._validate_not_future_date()

        if self._is_permission():
            self._set_permission_window_from_actual_gap()
            self._validate_no_duplicate_permission()
        else:
            self._resolve_shift()
            super().validate()

    def _validate_not_future_date(self):
        if self.reason == "Regularization":
            if getdate(self.from_date) > getdate(frappe.utils.today()) or getdate(self.to_date) > getdate(frappe.utils.today()):
                frappe.throw(_("Regularization requests cannot be created for future dates."))

    def before_submit(self):
        _validate_reason_allocation(self)

    def on_submit(self):
        behavior = _get_attendance_behavior(self)

        if behavior == "Tags Existing Attendance":
            self._tag_existing_attendance()
        else:
            self._smart_create_or_regularize_attendance()

    def on_cancel(self):
        behavior = _get_attendance_behavior(self)

        if behavior == "Tags Existing Attendance":
            self._remove_attendance_tags()
        else:
            self._smart_cancel_attendance()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _is_permission(self):
        reason_type = _get_reason_type_doc(self)
        return bool(reason_type) and reason_type.attendance_behavior == "Tags Existing Attendance"

    def _validate_single_date(self):
        if self.from_date != self.to_date:
            frappe.throw(
                _(
                    "This request type is allowed only for a single date. "
                    "From Date and To Date must be the same."
                )
            )

    def _resolve_shift(self):
        """Shift is hidden on the employee PWA, so it's never set from that
        form. Resolve it server-side from the employee's active Shift
        Assignment for the date, same as the shift lookups already used for
        the permission-gap and half-day-threshold calculations. Desk users
        who pick a shift explicitly are left alone."""
        shift_doc = _get_shift_doc(self.employee, self.from_date)
        if not self.shift:
            self.shift = shift_doc.name
        return shift_doc

    def _set_permission_window_from_actual_gap(self):
        """Late In / Early Out are always computed from real Employee
        Checkin data, never from user input — From Time / To Time / Hours
        are overwritten here regardless of what was submitted."""
        window = _get_actual_window(self.employee, self.from_date, self.reason)
        self.custom_permission_from_time = window["from_time"]
        self.custom_permission_to_time = window["to_time"]
        self.custom_permission_hours = window["hours"]

        if window["hours"] <= 0:
            frappe.throw(
                _("No late check-in or early check-out gap found for {0}.").format(
                    self.from_date
                )
            )

    def _validate_no_duplicate_permission(self):
        """Block duplicate Permission requests for the same employee and date (any type)."""
        reason_type = _get_reason_type_doc(self)
        sibling_reasons = frappe.get_all(
            "Attendance Reason Type Detail",
            filters={"parent": reason_type.name},
            pluck="reason",
        )

        existing = frappe.db.get_value(
            "Attendance Request",
            {
                "employee": self.employee,
                "from_date": self.from_date,
                "reason": ["in", sibling_reasons],
                "docstatus": ["!=", 2],
                "name": ["!=", self.name or ""],
            },
            "name",
        )
        if existing:
            frappe.throw(
                _(
                    "A Permission request already exists for "
                    "<b>{0}</b> on <b>{1}</b> ({2}). Only one permission "
                    "(Late In or Early Out) is allowed per date. "
                    "Please cancel the existing request before creating a new one."
                ).format(
                    self.employee_name or self.employee,
                    self.from_date,
                    existing,
                )
            )

    def _smart_create_or_regularize_attendance(self):
        """
        For 'Creates Attendance' type reasons (e.g. Regularization):
          - If an Absent record already exists for a date → update it to Present.
          - If no record exists yet (future / unprocessed date) → let parent
            create a fresh Present record via super().on_submit().

        This prevents the duplicate-attendance crash that occurs when Auto
        Attendance has already run and marked the employee Absent before the
        request is approved.
        """
        current = getdate(self.from_date)
        end = getdate(self.to_date)
        attendance_meta = frappe.get_meta("Attendance")
        has_unprocessed_dates = False

        while current <= end:
            existing = frappe.db.get_value(
                "Attendance",
                {
                    "employee": self.employee,
                    "attendance_date": current,
                    "docstatus": ["!=", 2],
                },
                ["name", "status"],
                as_dict=True,
            )

            if existing:
                if existing.status == "Absent":
                    update = {"status": "Present"}

                    if attendance_meta.has_field("custom_attendance_request"):
                        update["custom_attendance_request"] = self.name

                    frappe.db.set_value(
                        "Attendance",
                        existing.name,
                        update,
                        update_modified=False,
                    )

                    frappe.msgprint(
                        _(
                            "Attendance for <b>{0}</b> on <b>{1}</b> "
                            "updated from <b>Absent → Present</b>."
                        ).format(self.employee_name or self.employee, current),
                        indicator="green",
                        title=_("Attendance Regularized"),
                    )
                # If already Present / On Leave / etc. → leave untouched.

            else:
                # No record for this date yet; parent will create it.
                has_unprocessed_dates = True

            current += timedelta(days=1)

        if has_unprocessed_dates:
            # super().on_submit() loops the full date range internally.
            # It will only encounter dates that have no existing record
            # because we already handled all Absent ones above.
            super().on_submit()

    def _smart_cancel_attendance(self):
        """
        Reverse of _smart_create_or_regularize_attendance:
          - Records we changed from Absent → Present are reverted to Absent.
          - Records created fresh by super().on_submit() are cancelled via
            super().on_cancel().
        """
        current = getdate(self.from_date)
        end = getdate(self.to_date)
        attendance_meta = frappe.get_meta("Attendance")
        has_super_created = False

        while current <= end:
            filters = {
                "employee": self.employee,
                "attendance_date": current,
                "docstatus": ["!=", 2],
            }

            if attendance_meta.has_field("custom_attendance_request"):
                filters["custom_attendance_request"] = self.name

            existing = frappe.db.get_value(
                "Attendance",
                filters,
                ["name", "status"],
                as_dict=True,
            )

            if existing:
                # Determine whether this record pre-existed (was Absent before
                # we regularized it) or was newly created by super().
                # We detect pre-existing records by checking whether an
                # Employee Checkin log is absent — a simpler heuristic is to
                # revert to Absent and let Auto Attendance correct it on its
                # next run.  Either way, reverting to Absent is safe.
                update = {"status": "Absent"}

                if attendance_meta.has_field("custom_attendance_request"):
                    update["custom_attendance_request"] = None

                frappe.db.set_value(
                    "Attendance",
                    existing.name,
                    update,
                    update_modified=False,
                )
            else:
                # No tagged record found; super() may have created one.
                has_super_created = True

            current += timedelta(days=1)

        if has_super_created:
            super().on_cancel()

    def _tag_existing_attendance(self):
        """Used for 'Tags Existing Attendance' behavior (Permission type)."""
        attendance = frappe.db.get_value(
            "Attendance",
            {
                "employee": self.employee,
                "attendance_date": self.from_date,
                "docstatus": ["!=", 2],
            },
            "name",
        )

        if not attendance:
            frappe.throw(
                _(
                    "Attendance for <b>{0}</b> on <b>{1}</b> has not been "
                    "processed yet.\n\n"
                    "Auto Attendance runs after the shift ends for the day. "
                    "Please ask the manager to approve this request "
                    "after <b>{1}</b> end of day."
                ).format(
                    self.employee_name or self.employee,
                    self.from_date,
                )
            )

        attendance_meta = frappe.get_meta("Attendance")
        update = {
            "custom_permission_hours": flt(self.get("custom_permission_hours")),
        }

        if attendance_meta.has_field("custom_permission_type"):
            update["custom_permission_type"] = self.reason

        if attendance_meta.has_field("custom_attendance_request"):
            update["custom_attendance_request"] = self.name

        if attendance_meta.has_field("custom_permission_request"):
            update["custom_permission_request"] = self.name

        if attendance_meta.has_field("custom_permission_regularized"):
            update["custom_permission_regularized"] = 1

        if self.reason == "Late In":
            update["late_entry"] = 1
        elif self.reason == "Early Out":
            update["early_exit"] = 1

        frappe.db.set_value("Attendance", attendance, update, update_modified=False)

        frappe.msgprint(
            _(
                "Attendance tagged with <b>{0}</b> permission of "
                "<b>{1} hour(s)</b> on {2}."
            ).format(
                self.reason,
                self.get("custom_permission_hours"),
                self.from_date,
            ),
            indicator="green",
            title=_("Permission Applied"),
        )
        self._maybe_reverse_half_day(attendance)

    def _maybe_reverse_half_day(self, attendance_name):
        """Model B reversal: flip Half Day -> Present if in-window worked
        hours + permission credit clear the threshold."""
        att = frappe.db.get_value(
            "Attendance",
            attendance_name,
            ["status", "in_time", "out_time", "custom_absent_due_to_missing_checkout"],
            as_dict=True,
        )
        if not att or att.status != "Half Day":
            return
        if att.get("custom_absent_due_to_missing_checkout"):
            return
        if not att.in_time or not att.out_time:
            return

        shift_start, shift_end = _get_shift_window(self.employee, self.from_date)
        shift_doc = _get_shift_doc(self.employee, self.from_date)

        threshold = flt(shift_doc.working_hours_threshold_for_half_day)
        if threshold <= 0:
            return

        effective_in = max(get_datetime(att.in_time), shift_start)
        effective_out = min(get_datetime(att.out_time), shift_end)

        in_window_hours = time_diff_in_hours(effective_out, effective_in)
        if in_window_hours < 0:
            in_window_hours = 0.0

        permission_hours = flt(self.get("custom_permission_hours"))
        effective_hours = in_window_hours + permission_hours

        if effective_hours >= threshold:
            frappe.db.set_value(
                "Attendance",
                attendance_name,
                {"status": "Present", "leave_type": None},
                update_modified=False,
            )
            frappe.msgprint(
                _("Attendance for {0} reversed to Present.").format(self.from_date),
                indicator="green",
                title=_("Attendance Reversed"),
            )

    def _remove_attendance_tags(self):
        """Used for 'Tags Existing Attendance' cancel (Permission type)."""
        attendance_meta = frappe.get_meta("Attendance")

        filters = {
            "employee": self.employee,
            "attendance_date": self.from_date,
            "docstatus": ["!=", 2],
        }

        if attendance_meta.has_field("custom_attendance_request"):
            filters["custom_attendance_request"] = self.name
        elif attendance_meta.has_field("custom_permission_request"):
            filters["custom_permission_request"] = self.name

        attendance = frappe.db.get_value("Attendance", filters, "name")

        if not attendance:
            return

        update = {
            "custom_permission_hours": 0,
            # late_entry and early_exit are intentionally NOT reset here.
            # Auto Attendance sets those flags based on actual check-in/out
            # times. Cancelling a permission does not change the fact that
            # the employee was late or left early — it only removes the
            # recorded permission grant.
        }

        if attendance_meta.has_field("custom_permission_type"):
            update["custom_permission_type"] = ""

        if attendance_meta.has_field("custom_attendance_request"):
            update["custom_attendance_request"] = None

        if attendance_meta.has_field("custom_permission_request"):
            update["custom_permission_request"] = None

        if attendance_meta.has_field("custom_permission_regularized"):
            update["custom_permission_regularized"] = 0

        frappe.db.set_value(
            "Attendance",
            attendance,
            update,
            update_modified=False,
        )


# ----------------------------------------------------------------------
# module-level helpers
# ----------------------------------------------------------------------

def _get_attendance_behavior(doc):
    reason_type = _get_reason_type_doc(doc)
    if not reason_type:
        return "Creates Attendance"
    return reason_type.attendance_behavior or "Creates Attendance"


def _get_reason_type_doc(doc):
    lookup = doc.reason

    if not lookup:
        return None

    parent = frappe.db.get_value(
        "Attendance Reason Type Detail",
        filters={"reason": lookup},
        fieldname="parent",
    )

    if not parent:
        return None

    reason_type = frappe.get_doc("Attendance Reason Type", parent)
    return reason_type if reason_type.is_active else None


def _validate_reason_allocation(doc):
    reason_type = _get_reason_type_doc(doc)
    if not reason_type:
        return

    allocation = _get_allocation(doc, reason_type.name)
    if not allocation:
        frappe.throw(
            _(
                "No Attendance Reason Allocation found for <b>{0}</b>. "
                "Please contact HR."
            ).format(reason_type.type_name)
        )

    used_days, current_days = _count_period_usage(doc, reason_type, allocation)
    limit = int(flt(allocation.monthly_limit))

    if used_days + current_days > limit:
        frappe.throw(
            _(
                "Monthly limit exceeded for <b>{0}</b>.\n"
                "Limit: {1} days | Already used: {2} days | "
                "This request: {3} days | Total would be: {4} days"
            ).format(
                reason_type.type_name,
                limit,
                used_days,
                current_days,
                used_days + current_days,
            )
        )


def _get_allocation(doc, reason_type_name):
    request_date = getdate(doc.from_date)

    def fetch(extra_filters):
        results = frappe.get_all(
            "Attendance Reason Allocation",
            filters={
                "attendance_reason_type": reason_type_name,
                "company": doc.company,
                "docstatus": 1,
                "effective_from": ["<=", request_date],
                **extra_filters,
            },
            fields=["name", "monthly_limit", "effective_to", "period_start_day"],
            order_by="effective_from desc",
            limit=1,
        )

        if not results:
            return None

        alloc = results[0]

        if alloc.effective_to and getdate(alloc.effective_to) < request_date:
            return None

        return alloc

    alloc = fetch({"applies_to": "Employee", "employee": doc.employee})
    if alloc:
        return alloc

    dept = frappe.db.get_value("Employee", doc.employee, "department")
    if dept:
        alloc = fetch({"applies_to": "Department", "department": dept})
        if alloc:
            return alloc

    return fetch({"applies_to": "Company"})


def _get_period_window(request_date, period_start_day):
    request_date = getdate(request_date)
    day = max(1, min(int(period_start_day or 1), 28))

    def last_day(y, m):
        return calendar.monthrange(y, m)[1]

    def safe_date(y, m, d):
        return date(y, m, min(d, last_day(y, m)))

    current_start = safe_date(request_date.year, request_date.month, day)

    if request_date >= current_start:
        period_start = current_start

        if request_date.month == 12:
            ny, nm = request_date.year + 1, 1
        else:
            ny, nm = request_date.year, request_date.month + 1

        end_d = day - 1 if day > 1 else last_day(ny, nm)
        period_end = safe_date(ny, nm, end_d)
    else:
        if request_date.month == 1:
            py, pm = request_date.year - 1, 12
        else:
            py, pm = request_date.year, request_date.month - 1

        period_start = safe_date(py, pm, day)
        end_d = day - 1 if day > 1 else last_day(
            request_date.year,
            request_date.month,
        )
        period_end = safe_date(request_date.year, request_date.month, end_d)

    return period_start, period_end


def _count_period_usage(doc, reason_type, allocation):
    period_start_day = int(allocation.get("period_start_day") or 1)
    window_start, window_end = _get_period_window(doc.from_date, period_start_day)

    reasons = frappe.get_all(
        "Attendance Reason Type Detail",
        filters={"parent": reason_type.name},
        pluck="reason",
    )

    existing = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": doc.employee,
            "reason": ["in", reasons],
            "from_date": ["between", [window_start, window_end]],
            "docstatus": 1,
            "name": ["!=", doc.name],
        },
        fields=["from_date", "to_date"],
    )

    total_days = 0
    for req in existing:
        from_d = getdate(req.from_date)
        to_d = getdate(req.to_date)
        total_days += (to_d - from_d).days + 1

    current_days = (getdate(doc.to_date) - getdate(doc.from_date)).days + 1
    return total_days, current_days


def _get_actual_window(employee, permission_date, ptype):
    """Authoritative Late In / Early Out window: From Time, To Time, and
    Hours (clamped to 2) derived from the shift and real Employee Checkin
    data. Used both to populate the Attendance Request fields in validate()
    and (via get_permission_details) for the Desk live-preview call."""
    shift_start, shift_end = _get_shift_window(employee, permission_date)
    shift_doc = _get_shift_doc(employee, permission_date)

    def clamp_gap(value):
        return min(max(flt(value), 0.0), 2.0)

    if ptype == "Late In":
        grace_minutes = (
            frappe.utils.cint(shift_doc.late_entry_grace_period)
            if frappe.utils.cint(shift_doc.enable_late_entry_marking)
            else 0
        )
        allowed_in_time = shift_start + timedelta(minutes=grace_minutes)

        rows = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "log_type": "IN",
                "time": [
                    "between",
                    [
                        f"{permission_date} 00:00:00",
                        f"{permission_date} 23:59:59",
                    ],
                ],
            },
            fields=["time"],
            order_by="time asc",
            limit=1,
        )

        if not rows:
            return {
                "from_time": get_datetime_str(allowed_in_time),
                "to_time": get_datetime_str(allowed_in_time),
                "hours": 0.0,
                "raw_hours": 0.0,
                "checkin_found": False,
            }

        actual_in = get_datetime(rows[0].time)
        raw_gap = max(flt(time_diff_in_hours(actual_in, allowed_in_time)), 0.0)
        capped_hours = clamp_gap(raw_gap)
        capped_to_time = allowed_in_time + timedelta(hours=capped_hours)
        return {
            "from_time": get_datetime_str(allowed_in_time),
            "to_time": get_datetime_str(capped_to_time),
            "hours": capped_hours,
            "raw_hours": raw_gap,
            "checkin_found": True,
        }

    if ptype == "Early Out":
        grace_minutes = (
            frappe.utils.cint(shift_doc.early_exit_grace_period)
            if frappe.utils.cint(shift_doc.enable_early_exit_marking)
            else 0
        )
        allowed_out_time = shift_end - timedelta(minutes=grace_minutes)

        rows = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "log_type": "OUT",
                "time": [
                    "between",
                    [
                        f"{permission_date} 00:00:00",
                        f"{permission_date} 23:59:59",
                    ],
                ],
            },
            fields=["time"],
            order_by="time desc",
            limit=1,
        )

        if not rows:
            return {
                "from_time": get_datetime_str(allowed_out_time),
                "to_time": get_datetime_str(allowed_out_time),
                "hours": 0.0,
                "raw_hours": 0.0,
                "checkin_found": False,
            }

        actual_out = get_datetime(rows[0].time)
        raw_gap = max(flt(time_diff_in_hours(allowed_out_time, actual_out)), 0.0)
        capped_hours = clamp_gap(raw_gap)
        capped_from_time = allowed_out_time - timedelta(hours=capped_hours)
        return {
            "from_time": get_datetime_str(capped_from_time),
            "to_time": get_datetime_str(allowed_out_time),
            "hours": capped_hours,
            "raw_hours": raw_gap,
            "checkin_found": True,
        }

    return {
        "from_time": None,
        "to_time": None,
        "hours": 0.0,
        "raw_hours": 0.0,
        "checkin_found": False,
    }


def _get_shift_doc(employee, attendance_date):
    attendance_date = getdate(attendance_date)

    assignments = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": employee,
            "docstatus": 1,
            "start_date": ["<=", attendance_date],
        },
        fields=["shift_type", "end_date"],
        order_by="start_date desc",
    )

    active = [
        a for a in assignments
        if not a.end_date or getdate(a.end_date) >= attendance_date
    ]

    if len(active) > 1:
        frappe.throw(
            _(
                "Employee <b>{0}</b> has multiple overlapping Shift "
                "Assignments active on <b>{1}</b>. Please contact HR to "
                "resolve this before submitting this request."
            ).format(employee, attendance_date)
        )

    shift = active[0].shift_type if active else frappe.db.get_value(
        "Employee", employee, "default_shift"
    )

    if not shift:
        frappe.throw(
            _(
                "No Shift Assignment or Default Shift found for employee <b>{0}</b>. "
                "Please assign a shift before submitting this request."
            ).format(employee)
        )

    return frappe.get_doc("Shift Type", shift)


def _get_shift_window(employee, attendance_date):
    sd = _get_shift_doc(employee, attendance_date)
    start = get_datetime(f"{attendance_date} {sd.start_time}")
    end = get_datetime(f"{attendance_date} {sd.end_time}")

    if end <= start:
        end = end + timedelta(days=1)

    return start, end


@frappe.whitelist()
def get_permission_details(employee, permission_date, permission_type):
    window = _get_actual_window(employee, permission_date, permission_type)
    shift_start, shift_end = _get_shift_window(employee, permission_date)

    message = None
    if not window["checkin_found"]:
        message = _(
            "No check-in recorded yet — available hours will be calculated "
            "once the day's check-in data arrives."
        )
    elif window["raw_hours"] > 2:
        message = _(
            "Actual gap is {0} hours — permission will be capped at the "
            "2-hour limit."
        ).format(round(window["raw_hours"], 2))

    return {
        "permission_from_time": window["from_time"],
        "permission_to_time": window["to_time"],
        "permission_hours": round(flt(window["hours"]), 2),
        "shift_start": shift_start.strftime("%H:%M:%S"),
        "shift_end": shift_end.strftime("%H:%M:%S"),
        "message": message,
    }
