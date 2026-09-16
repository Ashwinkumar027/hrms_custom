import frappe
from frappe import _


def validate_self_approval(doc, method=None):
	if not doc.employee:
		return
	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if employee_user == frappe.session.user and frappe.session.user != "Administrator":
		frappe.throw(_("Self-approval for Compensatory Leave Requests is not allowed"))
