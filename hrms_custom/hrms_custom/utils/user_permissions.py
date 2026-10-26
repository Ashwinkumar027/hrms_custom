import frappe


def create_user_permission_for_employee(doc, method):
	"""
	Automatically creates User Permissions linking this Employee's user_id:
	1. To their own Employee record (restricting them to their own forms/records).
	2. To their specific Company (restricting them strictly to their own company).
	"""
	if not doc.user_id:
		return

	# 1. Employee User Permission
	exists_emp = frappe.db.exists(
		"User Permission",
		{"user": doc.user_id, "allow": "Employee", "for_value": doc.name}
	)
	if not exists_emp:
		frappe.get_doc({
			"doctype": "User Permission",
			"user": doc.user_id,
			"allow": "Employee",
			"for_value": doc.name,
			"apply_to_all_doctypes": 1
		}).insert(ignore_permissions=True)

	# 2. Company User Permission (Restricted to their particular company)
	if doc.company:
		exists_comp = frappe.db.exists(
			"User Permission",
			{"user": doc.user_id, "allow": "Company", "for_value": doc.company}
		)
		if not exists_comp:
			frappe.get_doc({
				"doctype": "User Permission",
				"user": doc.user_id,
				"allow": "Company",
				"for_value": doc.company,
				"is_default": 1,
				"apply_to_all_doctypes": 1
			}).insert(ignore_permissions=True)

	# 3. Ensure UI checkbox is synced to checked [✓]
	if hasattr(doc, "create_user_permission") and not doc.create_user_permission:
		doc.db_set("create_user_permission", 1, update_modified=False)
