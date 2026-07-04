import calendar
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, time_diff_in_hours

from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest


class CustomAttendanceRequest(AttendanceRequest):
    def validate(self):
        self._clean_request_type_fields()
        self._validate_not_future_date()

        if self._is_permission():
            self._validate_single_date()
            self._set_permission_hours_from_actual_gap()
            self._validate_permission_fields()
            self._validate_no_duplicate_permission()
            self._validate_permission_gap()
        elif self.reason == "Missed Check-In or Check-Out":
            self._validate_single_date()
            super().validate()
        else:
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
        return self.get("custom_request_type") == "Permission Request"

    def _clean_request_type_fields(self):
        if self.get("custom_request_type") == "Attendance Request":
            self.custom_permission_type = None

            if self.meta.has_field("custom_permission_hours"):
                self.custom_permission_hours = 0

        elif self.get("custom_request_type") == "Permission Request":
            self.reason = None

    def _validate_single_date(self):
        if self.from_date != self.to_date:
            frappe.throw(
                _(
                    "This request type is allowed only for a single date. "
                    "From Date and To Date must be the same."
                )
            )

    def _set_permission_hours_from_actual_gap(self):
        if flt(self.get("custom_permission_hours")) > 0:
            return

        self.custom_permission_hours = _get_actual_gap(self)

    def _validate_permission_fields(self):
        if not self.get("custom_permission_type"):
            frappe.throw(_("Permission Type (Late In / Early Out) is required."))

        hours = flt(self.get("custom_permission_hours"))
        if hours <= 0:
            frappe.throw(_("Permission hours must be greater than zero."))
        if hours > 2:
            frappe.throw(_("Permission cannot exceed 2 hours."))

    def _validate_permission_gap(self):
        gap = _get_actual_gap(self)
        if gap <= 0:
            frappe.throw(
                _("No late check-in or early check-out gap found for {0}.").format(
                    self.from_date
                )
            )

        if flt(self.get("custom_permission_hours")) > gap:
            frappe.throw(
                _(
                    "Permission hours ({0}) exceed actual gap ({1} hrs). "
                    "Please correct the hours."
                ).format(
                    self.get("custom_permission_hours"),
                    round(gap, 2),
                )
            )

    def _validate_no_duplicate_permission(self):
        """Block duplicate Permission requests for the same employee and date (any type)."""
        existing = frappe.db.get_value(
            "Attendance Request",
            {
                "employee": self.employee,
                "from_date": self.from_date,
                "custom_request_type": "Permission Request",
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
        For 'Creates Attendance' type reasons (e.g. Missed Check-In or Check-Out):
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
            update["custom_permission_type"] = self.get("custom_permission_type")

        if attendance_meta.has_field("custom_attendance_request"):
            update["custom_attendance_request"] = self.name

        if attendance_meta.has_field("custom_permission_request"):
            update["custom_permission_request"] = self.name

        if attendance_meta.has_field("custom_permission_regularized"):
            update["custom_permission_regularized"] = 1

        if self.get("custom_permission_type") == "Late In":
            update["late_entry"] = 1
        elif self.get("custom_permission_type") == "Early Out":
            update["early_exit"] = 1

        frappe.db.set_value("Attendance", attendance, update, update_modified=False)

        frappe.msgprint(
            _(
                "Attendance tagged with <b>{0}</b> permission of "
                "<b>{1} hour(s)</b> on {2}."
            ).format(
                self.get("custom_permission_type"),
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
    if doc.get("custom_request_type") == "Permission Request":
        lookup = doc.get("custom_permission_type")
    else:
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

    if doc.get("custom_request_type") == "Permission Request":
        existing = frappe.get_all(
            "Attendance Request",
            filters={
                "employee": doc.employee,
                "custom_request_type": "Permission Request",
                "custom_permission_type": ["in", reasons],
                "from_date": ["between", [window_start, window_end]],
                "docstatus": 1,
                "name": ["!=", doc.name],
            },
            fields=["from_date", "to_date"],
        )
    else:
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


def _get_actual_gap(doc):
    shift_start, shift_end = _get_shift_window(doc.employee, doc.from_date)
    shift_doc = _get_shift_doc(doc.employee, doc.from_date)
    ptype = doc.get("custom_permission_type")

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
                "employee": doc.employee,
                "log_type": "IN",
                "time": [
                    "between",
                    [
                        f"{doc.from_date} 00:00:00",
                        f"{doc.from_date} 23:59:59",
                    ],
                ],
            },
            fields=["time"],
            order_by="time asc",
            limit=1,
        )

        if not rows:
            return 0.0

        actual_in = get_datetime(rows[0].time)
        gap = time_diff_in_hours(actual_in, allowed_in_time)
        return clamp_gap(gap)

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
                "employee": doc.employee,
                "log_type": "OUT",
                "time": [
                    "between",
                    [
                        f"{doc.from_date} 00:00:00",
                        f"{doc.from_date} 23:59:59",
                    ],
                ],
            },
            fields=["time"],
            order_by="time desc",
            limit=1,
        )

        if not rows:
            return 0.0

        actual_out = get_datetime(rows[0].time)
        gap = time_diff_in_hours(allowed_out_time, actual_out)
        return clamp_gap(gap)

    return 0.0


def _get_shift_doc(employee, attendance_date):
    attendance_date = getdate(attendance_date)

    shift = None
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

    for assignment in assignments:
        if not assignment.end_date or getdate(assignment.end_date) >= attendance_date:
            shift = assignment.shift_type
            break

    if not shift:
        shift = frappe.db.get_value("Employee", employee, "default_shift")

    if not shift:
        frappe.throw(
            _(
                "No Shift Assignment or Default Shift found for employee <b>{0}</b>. "
                "Please assign a shift before applying permission."
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
    shift_start, shift_end = _get_shift_window(employee, permission_date)

    if permission_type == "Late In":
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

        from_t = shift_start.strftime("%H:%M:%S")

        if rows:
            actual_in = get_datetime(rows[0].time)
            gap_hours = min(time_diff_in_hours(actual_in, shift_start), 2.0)
            to_t = actual_in.strftime("%H:%M:%S")
        else:
            gap_hours = 2.0
            to_t = (shift_start + timedelta(hours=2)).strftime("%H:%M:%S")

    else:
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

        to_t = shift_end.strftime("%H:%M:%S")

        if rows:
            actual_out = get_datetime(rows[0].time)
            gap_hours = min(time_diff_in_hours(shift_end, actual_out), 2.0)
            from_t = actual_out.strftime("%H:%M:%S")
        else:
            gap_hours = 2.0
            from_t = (shift_end - timedelta(hours=2)).strftime("%H:%M:%S")

    return {
        "permission_from_time": from_t,
        "permission_to_time": to_t,
        "permission_hours": round(flt(gap_hours), 2),
        "shift_start": shift_start.strftime("%H:%M:%S"),
        "shift_end": shift_end.strftime("%H:%M:%S"),
    }
