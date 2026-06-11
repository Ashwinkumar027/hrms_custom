# Copyright (c) 2026, ASHWIN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class EmployeeAllowedShiftLocation(Document):
    def validate(self):
        if not self.applies_to:
            self.applies_to = "Employee"

        if self.applies_to == "Employee":
            if not self.employee:
                frappe.throw(_("Employee is required when Applies To is Employee."))
            self.company = None

        elif self.applies_to == "Company":
            if not self.company:
                frappe.throw(_("Company is required when Applies To is Company."))
            self.employee = None
            self.employee_name = None

        else:
            frappe.throw(_("Applies To must be Employee or Company."))

        if self.from_date and self.to_date and getdate(self.to_date) < getdate(self.from_date):
            frappe.throw(_("To Date cannot be before From Date."))

        self._move_legacy_location_to_table()

        if self.enabled and not self.get("locations"):
            frappe.throw(_("Add at least one Shift Location."))

    def _move_legacy_location_to_table(self):
        if not self.get("shift_location"):
            return

        existing = [row.shift_location for row in self.get("locations") if row.shift_location]
        if self.shift_location not in existing:
            self.append("locations", {"shift_location": self.shift_location})

        self.shift_location = None
