import frappe
from frappe.model.document import Document


class PolicyAcknowledgement(Document):
	def validate(self):
		if self.candidate_signature and self.read_confirmed:
			self.status = "Signed"
			if not self.date:
				self.date = frappe.utils.today()

	def before_insert(self):
		if frappe.db.exists(
			"Policy Acknowledgement", {"employee": self.employee, "policy": self.policy, "docstatus": ["!=", 2]}
		):
			frappe.throw(f"Acknowledgement for this policy already exists for employee {self.employee}")
