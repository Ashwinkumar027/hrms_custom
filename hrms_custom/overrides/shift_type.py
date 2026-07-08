import frappe
from frappe.utils import get_datetime, getdate

from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift, get_shift_details
from hrms.hr.doctype.shift_type.shift_type import ShiftType


class CustomShiftType(ShiftType):
    def get_start_and_end_dates(self, employee):
        """Returns start and end dates for checking attendance and marking absent
        return: start date = max of `process_attendance_after` and DOJ
        return: end date = the most recently *fully closed* shift occurrence.

        Stock HRMS instead resolves the occurrence one day before that (see
        the removed `- timedelta(days=1)` below), holding each day's Absent
        marking back until the following day's shift has also closed.
        `last_sync_of_checkin` is only ever advanced past a shift's actual
        end once that end has passed, so resolving directly against it here
        keeps that safety floor while dropping the extra day of delay.
        """
        date_of_joining, relieving_date, employee_creation = frappe.get_cached_value(
            "Employee", employee, ["date_of_joining", "relieving_date", "creation"]
        )

        if not date_of_joining:
            date_of_joining = employee_creation.date()

        start_date = max(getdate(self.process_attendance_after), date_of_joining)
        end_date = None

        shift_details = get_shift_details(self.name, get_datetime(self.last_sync_of_checkin))
        last_shift_time = (
            shift_details.actual_end if shift_details else get_datetime(self.last_sync_of_checkin)
        )

        # last_shift_time is already the actual_end of the occurrence that
        # last_sync_of_checkin just confirmed as closed - look it up directly.
        prev_shift = get_employee_shift(employee, last_shift_time, True, "reverse")
        if prev_shift and prev_shift.shift_type.name == self.name:
            end_date = (
                min(prev_shift.start_datetime.date(), relieving_date)
                if relieving_date
                else prev_shift.start_datetime.date()
            )
        else:
            # no shift found
            return None, None
        return start_date, end_date
