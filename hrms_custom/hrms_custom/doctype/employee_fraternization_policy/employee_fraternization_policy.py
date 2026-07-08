# Copyright (c) 2026, Aionion and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeFraternizationPolicy(Document):
	def validate(self):
		if self.signature and not self.policy_confirm:
			frappe.throw(
				"Please tick 'I have read and understood the above Employee "
				"Fraternization Policy' before signing."
			)

		if not self.policy_confirm:
			frappe.throw(
				"You must confirm that you have read and understood the "
				"policy before saving."
			)
