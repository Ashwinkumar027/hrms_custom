from collections import defaultdict

import frappe
from frappe.utils.nestedset import rebuild_tree


def find_tree_problems() -> dict:
	"""Inspect the Employee nested-set tree across all statuses and return detected anomalies.

	Returns an empty dict `{}` when the tree is healthy.
	"""
	rows = frappe.db.sql(
		"""
		SELECT name, status, reports_to, lft, rgt
		FROM `tabEmployee`
		ORDER BY name
		""",
		as_dict=True,
	)

	by_name = {row.name: row for row in rows}
	outside_manager_range = []
	invalid_lft_rgt = []
	value_occurrences = defaultdict(list)

	for row in rows:
		lft = row.lft
		rgt = row.rgt

		if lft is None or rgt is None or lft <= 0 or rgt <= 0 or lft >= rgt:
			invalid_lft_rgt.append(
				{
					"employee": row.name,
					"status": row.status,
					"reports_to": row.reports_to,
					"lft": lft,
					"rgt": rgt,
				}
			)

		if lft is not None:
			value_occurrences[lft].append({"employee": row.name, "field": "lft"})
		if rgt is not None:
			value_occurrences[rgt].append({"employee": row.name, "field": "rgt"})

		if row.reports_to:
			mgr = by_name.get(row.reports_to)
			if not mgr:
				outside_manager_range.append(
					{
						"employee": row.name,
						"status": row.status,
						"reports_to": row.reports_to,
						"emp_lft": lft,
						"emp_rgt": rgt,
						"mgr_lft": None,
						"mgr_rgt": None,
						"reason": "missing_manager",
					}
				)
			elif (
				lft is not None
				and rgt is not None
				and mgr.lft is not None
				and mgr.rgt is not None
				and not (lft > mgr.lft and rgt < mgr.rgt)
			):
				outside_manager_range.append(
					{
						"employee": row.name,
						"status": row.status,
						"reports_to": row.reports_to,
						"emp_lft": lft,
						"emp_rgt": rgt,
						"mgr_lft": mgr.lft,
						"mgr_rgt": mgr.rgt,
						"reason": "outside_manager_range",
					}
				)

	duplicate_numbers = [
		{
			"value": val,
			"count": len(occ),
			"occurrences": occ,
		}
		for val, occ in sorted(value_occurrences.items())
		if len(occ) > 1
	]

	problems = {}
	if outside_manager_range:
		problems["outside_manager_range"] = outside_manager_range
	if invalid_lft_rgt:
		problems["invalid_lft_rgt"] = invalid_lft_rgt
	if duplicate_numbers:
		problems["duplicate_numbers"] = duplicate_numbers

	return problems


def repair_if_broken() -> dict:
	"""Rebuild the Employee nested-set tree if any anomaly is detected.

	Clears Employee document cache and user_permissions cache only when a repair
	actually runs, and logs an Error Log entry titled 'Employee tree repaired'.
	"""
	before = find_tree_problems()
	if not before:
		return {"repaired": False, "before": {}, "after": {}}

	rebuild_tree("Employee")
	frappe.clear_document_cache("Employee")
	frappe.cache.delete_key("user_permissions")

	after = find_tree_problems()
	frappe.log_error(
		title="Employee tree repaired",
		message=frappe.as_json({"before": before, "after": after}),
	)
	return {"repaired": True, "before": before, "after": after}


def log_if_tree_broken(doc, method=None) -> None:
	"""Employee on_update hook to log the writer if saving leaves the tree broken."""
	if not getattr(doc, "reports_to", None):
		return

	emp_vals = frappe.db.get_value("Employee", doc.name, ["lft", "rgt"], as_dict=True)
	mgr_vals = frappe.db.get_value("Employee", doc.reports_to, ["lft", "rgt"], as_dict=True)

	emp_lft = emp_vals.lft if emp_vals else getattr(doc, "lft", None)
	emp_rgt = emp_vals.rgt if emp_vals else getattr(doc, "rgt", None)
	mgr_lft = mgr_vals.lft if mgr_vals else None
	mgr_rgt = mgr_vals.rgt if mgr_vals else None

	is_broken = (
		emp_lft is None
		or emp_rgt is None
		or mgr_lft is None
		or mgr_rgt is None
		or not (emp_lft > mgr_lft and emp_rgt < mgr_rgt)
	)
	if not is_broken:
		return

	frappe.log_error(
		title="Employee tree broken after save",
		message=frappe.as_json(
			{
				"employee": doc.name,
				"reports_to": doc.reports_to,
				"employee_lft_rgt": [emp_lft, emp_rgt],
				"manager_lft_rgt": [mgr_lft, mgr_rgt],
				"user": frappe.session.user,
				"cmd": frappe.form_dict.get("cmd") if getattr(frappe.local, "form_dict", None) else None,
				"in_import": bool(frappe.flags.in_import),
			}
		),
		reference_doctype="Employee",
		reference_name=doc.name,
	)
