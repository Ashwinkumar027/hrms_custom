import frappe


def diff_rows(old_rows, new_rows, label):
	"""
	Compares two lists of Salary Detail rows (earnings/deductions)
	and returns human readable change messages.
	"""
	old_map = {r.salary_component: r.amount for r in old_rows} if old_rows else {}
	new_map = {r.salary_component: r.amount for r in new_rows} if new_rows else {}

	messages = []

	for comp, amt in new_map.items():
		if comp not in old_map:
			messages.append(f"Added {label} component <b>{comp}</b>: ₹{amt}")

	for comp, amt in old_map.items():
		if comp not in new_map:
			messages.append(f"Removed {label} component <b>{comp}</b> (was ₹{amt})")

	for comp in old_map:
		if comp in new_map and old_map[comp] != new_map[comp]:
			messages.append(
				f"Changed {label} <b>{comp}</b> from ₹{old_map[comp]} to ₹{new_map[comp]}"
			)

	return messages


def log_salary_component_changes(doc, method):
	"""
	before_save hook on Salary Slip.
	Compares in-memory doc (new values) against the DB version (old values)
	and adds a readable comment listing exactly which components changed.
	"""
	if doc.is_new():
		return

	old_doc = frappe.get_doc("Salary Slip", doc.name)

	earning_msgs = diff_rows(old_doc.earnings, doc.earnings, "Earnings")
	deduction_msgs = diff_rows(old_doc.deductions, doc.deductions, "Deductions")

	all_msgs = earning_msgs + deduction_msgs

	if all_msgs:
		comment_text = "<br>".join(all_msgs)
		doc.add_comment("Info", comment_text)
