# Copyright (c) 2026, ASHWIN and contributors
# License: mit

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Employee ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
		{"label": _("Missing Document"), "fieldname": "missing_document", "fieldtype": "Data", "width": 200},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("company"):
		conditions.append("and e.company = %(company)s")
		values["company"] = filters["company"]
	if filters.get("department"):
		conditions.append("and e.department = %(department)s")
		values["department"] = filters["department"]
	condition_str = " ".join(conditions)

	employees = frappe.db.sql(
		f"select e.name as employee, e.employee_name, e.company, e.department "
		f"from `tabEmployee` e where e.status = 'Active' {condition_str}",
		values, as_dict=True,
	)

	mandatory_types = frappe.get_all("Document Type", filters={"is_mandatory": 1}, pluck="name")
	if not mandatory_types or not employees:
		return []

	existing_map = {}
	rows = frappe.db.sql(
		"""
		select parent as employee, document_type from `tabEmployee Document`
		where parenttype = 'Employee' and document_type in %(types)s
		""",
		{"types": mandatory_types}, as_dict=True,
	)
	for row in rows:
		existing_map.setdefault(row.employee, set()).add(row.document_type)

	data = []
	for emp in employees:
		uploaded = existing_map.get(emp.employee, set())
		for doc_type in mandatory_types:
			if doc_type not in uploaded:
				data.append({
					"employee": emp.employee, "employee_name": emp.employee_name,
					"company": emp.company, "department": emp.department,
					"missing_document": _("Missing {0}").format(doc_type),
				})
	return data
