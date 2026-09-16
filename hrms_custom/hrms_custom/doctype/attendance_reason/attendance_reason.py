# Copyright (c) 2026, ASHWIN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AttendanceReason(Document):
	"""
	Attendance Reason record.
	NOTE ON RENAMING:
	reason_name is set_only_once. If a reason ever needs renaming, it must be
	done via frappe.rename_doc("Attendance Reason", old_name, new_name) which
	safely cascades to all Link references, never via direct field edit.
	"""

	def validate(self):
		if not self.is_new() and self.has_value_changed("reason_name"):
			frappe.throw(
				_(
					"Reason Name cannot be edited directly after creation. "
					"Use the Rename tool (frappe.rename_doc) to ensure all linked records are updated."
				)
			)
