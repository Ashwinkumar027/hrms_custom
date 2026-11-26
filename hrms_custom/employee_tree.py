from collections import defaultdict

import frappe
from frappe.utils.nestedset import rebuild_tree


REPAIRABLE_KEYS = ("outside_manager_range", "invalid_lft_rgt", "duplicate_numbers")
UNREPAIRABLE_KEYS = ("reporting_loops", "missing_manager", "below_unrepairable")


def _classify_unrepairable_employees(rows: list[dict], by_name: dict[str, dict]) -> dict:
	"""Walk reports_to upward with cycle detection to isolate unrepairable rows."""
	reporting_loops = []
	missing_manager = []
	below_unrepairable = []
	unrepairable_names = set()

	for row in rows:
		if not row.reports_to:
			continue

		cur = row.name
		path = []
		visited_pos = {}

		while cur:
			if cur in visited_pos:
				cycle_start = visited_pos[cur]
				entry = {
					"employee": row.name,
					"status": row.status,
					"reports_to": row.reports_to,
					"lft": row.lft,
					"rgt": row.rgt,
				}
				if cycle_start == 0:
					entry["reason"] = "self_reporting" if len(path) == 1 else "reporting_loop"
					reporting_loops.append(entry)
				else:
					entry["reason"] = "below_reporting_loop"
					below_unrepairable.append(entry)
				unrepairable_names.add(row.name)
				break

			node = by_name.get(cur)
			if not node:
				entry = {
					"employee": row.name,
					"status": row.status,
					"reports_to": row.reports_to,
					"lft": row.lft,
					"rgt": row.rgt,
					"missing_ancestor": cur,
				}
				if len(path) == 1:
					entry["reason"] = "missing_manager"
					missing_manager.append(entry)
				else:
					entry["reason"] = "below_missing_manager"
					below_unrepairable.append(entry)
				unrepairable_names.add(row.name)
				break

			visited_pos[cur] = len(path)
			path.append(cur)
			cur = node.reports_to

	return {
		"reporting_loops": reporting_loops,
		"missing_manager": missing_manager,
		"below_unrepairable": below_unrepairable,
		"unrepairable_names": unrepairable_names,
	}


def find_tree_problems() -> dict:
	"""Inspect the Employee nested-set tree across all statuses and return detected anomalies.

	Isolates unrepairable rows (reporting_loops, missing_manager, below_unrepairable)
	first and checks outside_manager_range, invalid_lft_rgt, and duplicate_numbers
	only on repairable rows. Returns `{}` when the tree is healthy.
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
	classified = _classify_unrepairable_employees(rows, by_name)
	unrepairable_names = classified["unrepairable_names"]
	repairable_rows = [row for row in rows if row.name not in unrepairable_names]

	outside_manager_range = []
	invalid_lft_rgt = []
	value_occurrences = defaultdict(list)

	for row in repairable_rows:
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
			mgr = by_name[row.reports_to]
			if (
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
	if classified["reporting_loops"]:
		problems["reporting_loops"] = classified["reporting_loops"]
	if classified["missing_manager"]:
		problems["missing_manager"] = classified["missing_manager"]
	if classified["below_unrepairable"]:
		problems["below_unrepairable"] = classified["below_unrepairable"]
	if outside_manager_range:
		problems["outside_manager_range"] = outside_manager_range
	if invalid_lft_rgt:
		problems["invalid_lft_rgt"] = invalid_lft_rgt
	if duplicate_numbers:
		problems["duplicate_numbers"] = duplicate_numbers

	return problems


def repair_if_broken() -> dict:
	"""Rebuild the Employee nested-set tree when repairable anomalies exist.

	Clears Employee document cache and user_permissions cache only when a rebuild
	runs. Logs 'Employee tree unrepairable rows' at most once per 24 hours without
	rebuilding when only unrepairable rows exist.
	"""
	before = find_tree_problems()
	if not before:
		return {"repaired": False, "before": {}, "after": {}}

	has_repairable = any(k in before for k in REPAIRABLE_KEYS)
	if has_repairable:
		rebuild_tree("Employee")
		frappe.clear_document_cache("Employee")
		frappe.cache.delete_key("user_permissions")

		after = find_tree_problems()
		frappe.log_error(
			title="Employee tree repaired",
			message=frappe.as_json({"before": before, "after": after}),
		)
	else:
		after = before

	unrepairable_source = after if has_repairable else before
	unrepairable_payload = {k: unrepairable_source[k] for k in UNREPAIRABLE_KEYS if k in unrepairable_source}
	if unrepairable_payload and not frappe.cache.get_value("employee_tree_unrepairable", expires=True):
		frappe.cache.set_value("employee_tree_unrepairable", 1, expires_in_sec=86400)
		frappe.log_error(
			title="Employee tree unrepairable rows",
			message=frappe.as_json(unrepairable_payload),
		)

	return {"repaired": has_repairable, "before": before, "after": after}


def log_if_tree_broken(doc, method=None) -> None:
	"""Employee on_update hook to log the writer if saving leaves the tree broken.

	Rate-limited via Redis cache to at most one Error Log per employee every 24 hours.
	Never raises into the caller's Employee save transaction.
	"""
	try:
		if not getattr(doc, "reports_to", None):
			return

		cache_key = f"employee_tree_broken:{doc.name}"
		if frappe.cache.get_value(cache_key, expires=True):
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

		frappe.cache.set_value(cache_key, 1, expires_in_sec=86400)
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
	except Exception:
		try:
			fail_key = "employee_tree_hook_failed"
			if not frappe.cache.get_value(fail_key, expires=True):
				frappe.cache.set_value(fail_key, 1, expires_in_sec=3600)
				frappe.log_error(
					title="Employee tree hook failed",
					message=frappe.get_traceback(),
				)
		except Exception:
			pass
