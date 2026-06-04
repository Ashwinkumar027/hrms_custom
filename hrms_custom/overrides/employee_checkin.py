# Copyright (c) 2026, ASHWIN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from hrms.hr.doctype.employee_checkin.employee_checkin import (
    CheckinRadiusExceededError,
    EmployeeCheckin,
)
from hrms.hr.utils import get_distance_between_coordinates


class MultiLocationEmployeeCheckin(EmployeeCheckin):
    def validate_distance_from_shift_location(self):
        if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
            return

        if not (self.latitude or self.longitude):
            frappe.throw(_("Latitude and longitude values are required for checking in."))

        if not self.employee or not self.shift:
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
                ["checkin_radius", "latitude", "longitude"],
                as_dict=True,
            )

            if not location:
                continue

            if not location.latitude or not location.longitude:
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
    locations = []

    # Check custom multi-location DocType first
    if frappe.db.exists("DocType", "Employee Allowed Shift Location"):
        locations = frappe.get_all(
            "Employee Allowed Shift Location",
            filters={
                "employee": employee,
                "shift_type": shift_type,
                "enabled": 1,
                "from_date": ["<=", checkin_date],
            },
            or_filters=[
                ["to_date", ">=", checkin_date],
                ["to_date", "is", "not set"],
            ],
            pluck="shift_location",
        )

    if locations:
        return remove_duplicates(locations)

    # Fallback: standard Shift Assignment location (original HRMS behaviour)
    assignment_locations = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": employee,
            "shift_type": shift_type,
            "start_date": ["<=", checkin_date],
            "shift_location": ["is", "set"],
            "docstatus": 1,
            "status": "Active",
        },
        or_filters=[
            ["end_date", ">=", checkin_date],
            ["end_date", "is", "not set"],
        ],
        pluck="shift_location",
    )

    return remove_duplicates(assignment_locations)


def remove_duplicates(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
