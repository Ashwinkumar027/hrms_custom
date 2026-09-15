import frappe


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	allowed_roles = ["HR Manager", "HR User", "System Manager", "Administrator"]
	user_roles = frappe.get_roles(user)

	if any(role in user_roles for role in allowed_roles):
		return ""

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return "1=0"

	employee_escaped = frappe.db.escape(employee)
	return f"`tabAttendance`.`employee` = {employee_escaped}"
