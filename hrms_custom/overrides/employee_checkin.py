# Copyright (c) 2026, ASHWIN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, add_to_date

from hrms.hr.doctype.employee_checkin.employee_checkin import (
    CheckinRadiusExceededError,
    EmployeeCheckin,
)
from hrms.hr.utils import get_distance_between_coordinates


class MultiLocationEmployeeCheckin(EmployeeCheckin):

    def validate(self):
        super().validate()
        self.block_late_checkout()

    def block_late_checkout(self):
        if frappe.db.get_single_value("HR Settings", "custom_disable_checkout_window_guard"):
            return

        if self.log_type != "OUT" or not self.employee:
            return

        last_in = frappe.db.get_value(
            "Employee Checkin",
            {"employee": self.employee, "log_type": "IN", "time": ["<", self.time]},
            ["name", "time", "shift"],
            order_by="time desc",
            as_dict=True,
        )
        if not last_in or not last_in.shift:
            return

        shift = frappe.db.get_value(
            "Shift Type",
            last_in.shift,
            ["end_time", "allow_check_out_after_shift_end_time"],
            as_dict=True,
        )
        if not shift:
            return

        shift_date = getdate(last_in.time)
        shift_end = get_datetime(f"{shift_date} {shift.end_time}")
        cutoff = add_to_date(shift_end, minutes=shift.allow_check_out_after_shift_end_time or 0)

        if get_datetime(self.time) > cutoff:
            frappe.throw(
                _(
                    "Checkout window for {0} closed at {1}. "
                    "That day will be marked Absent. Please check in for your next shift."
                ).format(shift_date.strftime("%d-%m-%Y"), cutoff.strftime("%H:%M")),
                title=_("Checkout window closed"),
            )

    def validate_distance_from_shift_location(self):
        if self.custom_auto_closed:
            return

        if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
            return

        if self.latitude in (None, "") or self.longitude in (None, ""):
            frappe.throw(_("Latitude and longitude values are required for checking in/out."))

        if not self.employee:
            return

        allowed_locations = get_allowed_shift_locations(
            employee=self.employee,
            shift_type=self.shift,
            checkin_time=self.time,
        )

        if not allowed_locations:
            return

        checkin_latitude = flt(self.latitude)
        checkin_longitude = flt(self.longitude)

        nearest_location = None
        nearest_distance = None

        for location_name in allowed_locations:
            location = frappe.db.get_value(
                "Shift Location",
                location_name,
                ["checkin_radius", "latitude", "longitude", "custom_no_geofence"],
                as_dict=True,
            )

            if not location:
                continue

            if location.custom_no_geofence:
                if frappe.get_meta("Employee Checkin").has_field("custom_validated_shift_location"):
                    self.custom_validated_shift_location = location_name
                return

            if location.latitude in (None, "") or location.longitude in (None, ""):
                continue

            checkin_radius = flt(location.checkin_radius)
            if checkin_radius <= 0:
                continue

            distance = get_distance_between_coordinates(
                flt(location.latitude),
                flt(location.longitude),
                checkin_latitude,
                checkin_longitude,
            )

            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_location = location_name

            if distance <= checkin_radius:
                # Store which location matched — only if custom field exists
                if frappe.get_meta("Employee Checkin").has_field("custom_validated_shift_location"):
                    self.custom_validated_shift_location = location_name
                return

        # All locations checked — employee is outside all of them
        if nearest_location:
            frappe.throw(
                _(
                    "You are outside all allowed shift locations. "
                    "Nearest allowed location is {0}, approximately {1} meters away."
                ).format(frappe.bold(nearest_location), round(nearest_distance, 2)),
                exc=CheckinRadiusExceededError,
            )

        frappe.throw(
            _("No valid shift location with latitude, longitude, and radius was found."),
            exc=CheckinRadiusExceededError,
        )


def get_allowed_shift_locations(employee, shift_type, checkin_time):
    checkin_date = getdate(checkin_time)

    if frappe.db.exists("DocType", "Employee Allowed Shift Location"):
        employee_locations = get_locations_from_allowed_location_docs(
            {
                "employee": employee,
                "shift_type": shift_type,
                "enabled": 1,
                "from_date": ["<=", checkin_date],
            },
            checkin_date,
        )

        if employee_locations:
            return employee_locations

        company = frappe.db.get_value("Employee", employee, "company")
        if company:
            company_locations = get_locations_from_allowed_location_docs(
                {
                    "applies_to": "Company",
                    "company": company,
                    "shift_type": shift_type,
                    "enabled": 1,
                    "from_date": ["<=", checkin_date],
                },
                checkin_date,
            )

            if company_locations:
                return company_locations

    # Fallback: standard Shift Assignment location (original HRMS behaviour)
    assignment_filters = {
        "employee": employee,
        "start_date": ["<=", checkin_date],
        "shift_location": ["is", "set"],
        "docstatus": 1,
        "status": "Active",
    }
    if shift_type:
        assignment_filters["shift_type"] = shift_type

    assignment_locations = frappe.get_all(
        "Shift Assignment",
        filters=assignment_filters,
        or_filters=[
            ["end_date", ">=", checkin_date],
            ["end_date", "is", "not set"],
        ],
        pluck="shift_location",
    )

    return remove_duplicates(assignment_locations)


def get_locations_from_allowed_location_docs(filters, checkin_date):
    docs = frappe.get_all(
        "Employee Allowed Shift Location",
        filters=filters,
        or_filters=[
            ["to_date", ">=", checkin_date],
            ["to_date", "is", "not set"],
        ],
        fields=["name", "shift_location"],
    )

    if not docs:
        return []

    locations = [doc.shift_location for doc in docs if doc.shift_location]
    parent_names = [doc.name for doc in docs]

    if frappe.db.exists("DocType", "Employee Allowed Shift Location Detail"):
        locations.extend(
            frappe.get_all(
                "Employee Allowed Shift Location Detail",
                filters={
                    "parent": ["in", parent_names],
                    "parenttype": "Employee Allowed Shift Location",
                    "parentfield": "locations",
                },
                pluck="shift_location",
            )
        )

    return remove_duplicates(locations)


def remove_duplicates(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
