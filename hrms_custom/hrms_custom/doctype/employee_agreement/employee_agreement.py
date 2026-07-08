import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class EmployeeAgreement(Document):
	def validate(self):
		if self.employee_signature and not self.date:
			self.date = today()

	def before_insert(self):
		if frappe.db.exists("Employee Agreement", {"employee": self.employee, "docstatus": ["!=", 2]}):
			frappe.throw(_("An Employee Agreement already exists for {0}").format(self.employee))
