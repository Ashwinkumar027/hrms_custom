# Copyright (c) 2026, ASHWIN and contributors
# License: mit

import frappe
from frappe import _
from frappe.utils import date_diff, today


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Employee ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
		{"label": _("Document Type"), "fieldname": "document_type", "fieldtype": "Link", "options": "Document Type", "width": 150},
		{"label": _("Expiry Date"), "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
		{"label": _("Days Remaining"), "fieldname": "days_remaining", "fieldtype": "Int", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	conditions = ["ed.expiry_date is not null"]
	values = {}
	if filters.get("company"):
		conditions.append("e.company = %(company)s")
		values["company"] = filters["company"]
	if filters.get("document_type"):
		conditions.append("ed.document_type = %(document_type)s")
		values["document_type"] = filters["document_type"]
	condition_str = " and ".join(conditions)

	rows = frappe.db.sql(
		f"""
		select e.name as employee, e.employee_name, ed.document_type, ed.expiry_date, ed.status
		from `tabEmployee Document` ed
		inner join `tabEmployee` e on e.name = ed.parent
		where ed.parenttype = 'Employee' and {condition_str}
		order by ed.expiry_date asc
		""",
		values, as_dict=True,
	)

	days_remaining_filter = filters.get("days_remaining")
	data = []
	for row in rows:
		days_remaining = date_diff(row.expiry_date, today())
		row["days_remaining"] = days_remaining
		if days_remaining_filter and days_remaining > frappe.utils.cint(days_remaining_filter):
			continue
		if days_remaining < 0:
			row["status"] = "Expired"
			row["indicator"] = "red"
		elif days_remaining <= 30:
			row["indicator"] = "orange"
		else:
			row["indicator"] = "green"
		data.append(row)
	return data
