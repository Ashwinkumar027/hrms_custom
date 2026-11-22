import frappe


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	# System Managers, HR Managers, HR Users, and Administrator have global access
	allowed_roles = ["HR Manager", "HR User", "System Manager", "Administrator"]
	user_roles = frappe.get_roles(user)
	if any(role in user_roles for role in allowed_roles):
		return ""

	# Find employee linked to the logged-in user account
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		# If user has no linked Employee record and is not HR, return impossible condition (deny all)
		return "1=0"

	# Restrict standard employees strictly to their own agreements
	return f"`tabEmployee Agreement`.employee = {frappe.db.escape(employee)}"


def has_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user

	allowed_roles = ["HR Manager", "HR User", "System Manager", "Administrator"]
	user_roles = frappe.get_roles(user)
	if any(role in user_roles for role in allowed_roles):
		return True

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return False

	# Allow employees to create new agreements for themselves
	if ptype == "create":
		return True

	# For read/write/submit/cancel: only allow if doc belongs to this employee
	doc_emp = doc.get("employee") if hasattr(doc, "get") else getattr(doc, "employee", None)
	if not doc_emp:
		return True
	return doc_emp == employee


