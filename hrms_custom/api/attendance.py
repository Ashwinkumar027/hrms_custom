# Copyright (c) 2026, ASHWIN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


@frappe.whitelist()
def get_allocated_reasons(employee=None, as_dict=False):
	"""
	Shared allocation resolution function used by both Desk and PWA.
	Resolves active Attendance Reason records allocated to an employee based on
	the hierarchy: Employee > Department > Company.

	Date range check:
	effective_from <= today and (effective_to IS NULL or effective_to >= today).

	Option B:
	All allocated reasons remain visible in the dropdown. Quota enforcement
	occurs as a hard block in before_submit with a descriptive limit error.

	Returns:
	- List of Attendance Reason name values (Link identifiers), or
	- If as_dict is True: list of dicts [{"label": r.reason_name, "value": r.name}]
	"""
	if not employee:
		if frappe.session.user == "Administrator":
			emp_name = frappe.db.get_value(
				"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
			)
			if emp_name:
				employee = emp_name
		else:
			employee = frappe.db.get_value(
				"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
			)

	if not employee:
		# If user is Administrator without an employee record, return all active reasons
		if frappe.session.user == "Administrator":
			reasons = frappe.get_all(
				"Attendance Reason",
				filters={"is_active": 1},
				fields=["name", "reason_name", "attendance_reason_type"],
				order_by="idx asc, reason_name asc",
			)
			if as_dict:
				return [{"label": r.reason_name, "value": r.name} for r in reasons]
			return [r.name for r in reasons]
		return []

	emp_doc = frappe.db.get_value(
		"Employee", employee, ["name", "company", "department"], as_dict=True
	)
	if not emp_doc:
		return []

	today = getdate(frappe.utils.today())

	# Fetch all submitted allocations for this company
	# Hierarchy precedence: Employee > Department > Company
	# Date check: effective_from <= today and (effective_to is null or effective_to >= today)
	allocs = frappe.db.sql(
		"""
		SELECT
			name,
			attendance_reason_type,
			applies_to,
			employee,
			department,
			company,
			effective_from,
			effective_to,
			monthly_limit
		FROM `tabAttendance Reason Allocation`
		WHERE docstatus = 1
			AND company = %(company)s
			AND effective_from <= %(today)s
			AND (effective_to IS NULL OR effective_to = '' OR effective_to >= %(today)s)
			AND (
				(applies_to = 'Employee' AND employee = %(employee)s)
				OR (applies_to = 'Department' AND department = %(department)s)
				OR (applies_to = 'Company')
			)
		ORDER BY effective_from DESC
		""",
		{
			"company": emp_doc.company,
			"today": today,
			"employee": emp_doc.name,
			"department": emp_doc.department or "",
		},
		as_dict=True,
	)

	if not allocs:
		return []

	# Group allocations by attendance_reason_type with hierarchy: Employee > Department > Company
	# For each type, the most specific one wins (do not merge/duplicate)
	winning_allocs = {}
	priority_map = {"Employee": 1, "Department": 2, "Company": 3}

	for a in allocs:
		rtype = a.attendance_reason_type
		prio = priority_map.get(a.applies_to, 99)

		if rtype not in winning_allocs:
			winning_allocs[rtype] = (prio, a)
		else:
			existing_prio, _ = winning_allocs[rtype]
			if prio < existing_prio:
				winning_allocs[rtype] = (prio, a)

	if not winning_allocs:
		return []

	winning_types = list(winning_allocs.keys())

	# Only include reason types that are active
	active_types = frappe.get_all(
		"Attendance Reason Type",
		filters={"name": ["in", winning_types], "is_active": 1, "docstatus": ["<", 2]},
		pluck="name",
	)

	if not active_types:
		return []

	# Resolve Attendance Reason records for active winning types
	reasons = frappe.get_all(
		"Attendance Reason",
		filters={"attendance_reason_type": ["in", active_types], "is_active": 1},
		fields=["name", "reason_name", "attendance_reason_type"],
		order_by="idx asc, reason_name asc",
	)

	if as_dict:
		return [{"label": r.reason_name, "value": r.name} for r in reasons]

	return [r.name for r in reasons]


@frappe.whitelist()
def attendance_reason_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Custom query for Attendance Request.reason Link field in Desk.
	Uses get_allocated_reasons to return only the reasons allocated to the employee.
	"""
	employee = (filters or {}).get("employee")
	allocated_reason_names = get_allocated_reasons(employee=employee, as_dict=False)

	if not allocated_reason_names:
		return []

	txt_lower = (txt or "").lower().strip()
	out = []
	for name in allocated_reason_names:
		if not txt_lower or txt_lower in name.lower():
			out.append((name, name))

	return out[start : start + page_len]
