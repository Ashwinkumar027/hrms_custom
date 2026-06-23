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
		{"label": _("Document Type"), "fieldname": "document_type", "fieldtype": "Link", "options": "Document Type", "width": 150},
		{"label": _("Document Number"), "fieldname": "document_number", "fieldtype": "Data", "width": 140},
		{"label": _("Expiry Date"), "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Attachment"), "fieldname": "attachment", "fieldtype": "Data", "width": 200},
	]


def get_data(filters):
	conditions, values = build_conditions(filters)
	return frappe.db.sql(
		f"""
		select e.name as employee, e.employee_name, e.company, e.department,
			ed.document_type, ed.document_number, ed.expiry_date, ed.status, ed.attachment
		from `tabEmployee Document` ed
		inner join `tabEmployee` e on e.name = ed.parent
		where ed.parenttype = 'Employee' {conditions}
		order by e.employee_name asc
		""",
		values, as_dict=True,
	)


def build_conditions(filters):
	conditions = []
	values = {}
	mapping = {
		"company": "e.company", "branch": "e.branch", "department": "e.department",
		"employee": "e.name", "document_type": "ed.document_type", "status": "ed.status",
	}
	for key, column in mapping.items():
		if filters.get(key):
			conditions.append(f"and {column} = %({key})s")
			values[key] = filters[key]
	return " ".join(conditions), values
