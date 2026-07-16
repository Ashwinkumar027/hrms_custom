# Copyright (c) 2026, Aionion and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from hrms_custom.hrms_custom.utils.signature_utils import merge_or_allow_insert


class EmployeeFraternizationPolicy(Document):
	def validate(self):
		if self.signature and self.signature_upload:
			frappe.throw(
				"Please provide only one signature — either draw or upload, not both."
			)

		if (self.signature or self.signature_upload) and not self.policy_confirm:
			frappe.throw(
				"Please tick 'I have read and understood the above Employee "
				"Fraternization Policy' before signing."
			)

		if not self.policy_confirm:
			frappe.throw(
				"You must confirm that you have read and understood the "
				"policy before saving."
			)

	def before_insert(self):
		merge_or_allow_insert(self, route="employee-fraternization-policy")
