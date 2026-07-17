import frappe
from frappe.model.document import Document


class TAReimbursementClaim(Document):
	def validate(self):
		self.calculate_total_amount()
		self.validate_remarks_on_reject_or_hold()
		self.validate_client_visit_proposal()

	def calculate_total_amount(self):
		total = 0
		for row in self.travel_claim_details:
			total += row.amount or 0
		self.total_amount = total

	def validate_remarks_on_reject_or_hold(self):
		reject_states = [
			"RM Rejected",
			"Admin Rejected",
			"Accounts Rejected",
			"On Hold",
		]
		if self.status in reject_states and not self.remarks:
			frappe.throw(
				f"Remarks are mandatory when setting status to '{self.status}'. "
				"Please provide a reason."
			)

	def validate_client_visit_proposal(self):
		if self.client_visit_proposal:
			proposal_status = frappe.db.get_value(
				"Client Visit Proposal", self.client_visit_proposal, "status"
			)
			if proposal_status != "Approved":
				frappe.throw(
					f"Client Visit Proposal {self.client_visit_proposal} is not Approved "
					f"(current status: {proposal_status}). Only approved proposals can be linked."
				)
