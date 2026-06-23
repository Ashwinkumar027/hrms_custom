# Copyright (c) 2026, ASHWIN and contributors
# License: mit

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, today

EXPIRY_WINDOW_DAYS = 30
EXPIRY_WATCHED_TYPES = ["Passport", "Driving License"]


def send_document_alerts():
	"""Daily scheduler job: notify HR Manager about documents expiring soon
	and employees missing mandatory documents."""
	hr_manager_emails = get_hr_manager_emails()
	if not hr_manager_emails:
		return

	expiring_rows = get_expiring_documents()
	missing_rows = get_missing_mandatory_documents()
	if not expiring_rows and not missing_rows:
		return

	frappe.sendmail(
		recipients=hr_manager_emails,
		subject=_("Employee Document Alerts - {0}").format(today()),
		message=build_email_message(expiring_rows, missing_rows),
	)


def get_hr_manager_emails():
	users = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"}, pluck="parent")
	emails = []
	for user in users:
		if user and user != "Administrator" and frappe.db.get_value("User", user, "enabled"):
			emails.append(user)
	return emails


def get_expiring_documents():
	cutoff_date = add_days(today(), EXPIRY_WINDOW_DAYS)
	rows = frappe.db.sql(
		"""
		select e.name as employee, e.employee_name, ed.document_type, ed.expiry_date
		from `tabEmployee Document` ed
		inner join `tabEmployee` e on e.name = ed.parent
		where ed.parenttype = 'Employee' and ed.document_type in %(types)s
			and ed.expiry_date is not null
			and ed.expiry_date between %(today)s and %(cutoff)s
			and e.status = 'Active'
		order by ed.expiry_date asc
		""",
		{"types": EXPIRY_WATCHED_TYPES, "today": today(), "cutoff": cutoff_date}, as_dict=True,
	)
	for row in rows:
		row["days_remaining"] = date_diff(row.expiry_date, today())
	return rows


def get_missing_mandatory_documents():
	mandatory_types = frappe.get_all("Document Type", filters={"is_mandatory": 1}, pluck="name")
	if not mandatory_types:
		return []
	employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name"])
	if not employees:
		return []

	existing_map = {}
	rows = frappe.db.sql(
		"select parent as employee, document_type from `tabEmployee Document` "
		"where parenttype = 'Employee' and document_type in %(types)s",
		{"types": mandatory_types}, as_dict=True,
	)
	for row in rows:
		existing_map.setdefault(row.employee, set()).add(row.document_type)

	missing = []
	for emp in employees:
		uploaded = existing_map.get(emp.name, set())
		for doc_type in mandatory_types:
			if doc_type not in uploaded:
				missing.append({"employee": emp.name, "employee_name": emp.employee_name, "document_type": doc_type})
	return missing


def build_email_message(expiring_rows, missing_rows):
	parts = []
	if expiring_rows:
		parts.append("<h4>" + _("Documents Expiring Within 30 Days") + "</h4>")
		parts.append("<table border='1' cellpadding='5' style='border-collapse:collapse;width:100%'>")
		parts.append("<tr><th>{0}</th><th>{1}</th><th>{2}</th><th>{3}</th></tr>".format(
			_("Employee"), _("Name"), _("Document Type"), _("Expiry Date")))
		for row in expiring_rows:
			parts.append("<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(
				row.employee, row.employee_name, row.document_type, row.expiry_date))
		parts.append("</table><br>")

	if missing_rows:
		parts.append("<h4>" + _("Employees Missing Mandatory Documents") + "</h4>")
		parts.append("<table border='1' cellpadding='5' style='border-collapse:collapse;width:100%'>")
		parts.append("<tr><th>{0}</th><th>{1}</th><th>{2}</th></tr>".format(_("Employee"), _("Name"), _("Missing Document")))
		for row in missing_rows:
			parts.append("<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>".format(
				row["employee"], row["employee_name"], row["document_type"]))
		parts.append("</table>")
	return "".join(parts)
