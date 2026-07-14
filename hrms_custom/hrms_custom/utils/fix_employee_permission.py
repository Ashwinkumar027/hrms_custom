import frappe


def fix_employee_role_permission():
	"""
	HRMS's core Employee doctype standard permission sets if_owner=1 for the
	Employee role, which gets re-synced on every bench migrate, silently
	undoing our fix. This keeps it corrected: employees should see their own
	record via the custom permission_query_conditions (matched on user_id),
	not via record ownership.
	"""
	doc = frappe.get_doc("Custom DocPerm", {"parent": "Employee", "role": "Employee"})
	if doc.if_owner:
		doc.if_owner = 0
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache(doctype="Employee")
