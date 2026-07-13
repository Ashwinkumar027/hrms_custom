import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today
from hrms_custom.hrms_custom.utils.signature_utils import merge_or_allow_insert


class EmployeeAgreement(Document):
	def validate(self):
		if self.employee_signature and not self.date:
			self.date = today()

	def before_insert(self):
		merge_or_allow_insert(self, route="employee-agreement-form")
