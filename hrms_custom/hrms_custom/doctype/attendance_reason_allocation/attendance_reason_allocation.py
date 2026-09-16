# Copyright (c) 2026, ASHWIN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists


class AttendanceReasonAllocation(Document):
	def autoname(self):
		"""Auto-names Attendance Reason Allocation records based on applies_to:
		- Company: {Company Abbr}-{Attendance Reason Type}
		- Department: {Department}-{Attendance Reason Type}
		- Employee: {Employee}-{Attendance Reason Type}
		- Fallback: ARA-{Attendance Reason Type}
		Appends sequential suffix (-1, -2) automatically if duplicate exists.
		"""
		if self.applies_to == "Company":
			if not self.company:
				frappe.throw(_("Company is required when Applies To is 'Company'."))

			abbr = (frappe.db.get_value("Company", self.company, "abbr") or "").strip()
			if not abbr:
				frappe.throw(
					_(
						"Cannot generate document name: Company <b>{0}</b> does not have an Abbreviation (abbr) configured. "
						"Please set the Abbreviation in the Company document first."
					).format(self.company),
					title=_("Missing Company Abbreviation"),
				)
			base_name = f"{abbr}-{self.attendance_reason_type}"

		elif self.applies_to == "Department" and self.department:
			base_name = f"{self.department}-{self.attendance_reason_type}"

		elif self.applies_to == "Employee" and self.employee:
			base_name = f"{self.employee}-{self.attendance_reason_type}"

		else:
			base_name = f"ARA-{self.attendance_reason_type}"

		self.name = append_number_if_name_exists("Attendance Reason Allocation", base_name)
