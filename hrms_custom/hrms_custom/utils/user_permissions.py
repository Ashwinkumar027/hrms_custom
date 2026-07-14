import frappe


def create_user_permission_for_employee(doc, method):
	"""
	Automatically creates a User Permission linking this Employee's user_id
	to their own Employee record, restricting them to their own onboarding
	form records (Employee Registration Form, ESI Enrollment, etc.) since
	those doctypes have an 'employee' Link field.

	apply_to_all_doctypes=1 means this restriction cascades to every doctype
	that links to Employee, not just Employee itself.
	"""
	if not doc.user_id:
		return

	exists = frappe.db.exists(
		"User Permission",
		{"user": doc.user_id, "allow": "Employee", "for_value": doc.name}
	)
	if exists:
		return

	frappe.get_doc({
		"doctype": "User Permission",
		"user": doc.user_id,
		"allow": "Employee",
		"for_value": doc.name,
		"apply_to_all_doctypes": 1
	}).insert(ignore_permissions=True)
