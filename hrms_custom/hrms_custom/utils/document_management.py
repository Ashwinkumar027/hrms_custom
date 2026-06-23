# Copyright (c) 2026, ASHWIN and contributors
# License: mit
#
# Whitelisted endpoints for bulk ZIP download and the document dashboard.
# Called as hrms_custom.hrms_custom.utils.document_management.<func>

import io
import os
import zipfile

import frappe
from frappe import _
from frappe.utils import add_days, today
from frappe.utils.file_manager import get_file_path

ALLOWED_DOWNLOAD_ROLES = {"HR Manager", "HR User", "System Manager"}


def _check_download_permission():
	if not ALLOWED_DOWNLOAD_ROLES & set(frappe.get_roles(frappe.session.user)):
		frappe.throw(
			_("You are not permitted to download bulk employee documents."), frappe.PermissionError
		)


def _get_documents(employee_names, document_type=None):
	"""Fetch Employee Document rows for the given employees, optionally
	filtered to a single Document Type."""
	conditions = ""
	values = {"employees": employee_names}

	if document_type:
		conditions = "and document_type = %(document_type)s"
		values["document_type"] = document_type

	return frappe.db.sql(
		f"""
		select parent as employee, document_type, attachment
		from `tabEmployee Document`
		where parenttype = 'Employee' and parent in %(employees)s
			and attachment is not null and attachment != ''
			{conditions}
		""",
		values,
		as_dict=True,
	)


def _build_zip(documents, single_employee=False):
	"""Build a ZIP in memory.
	- If single_employee: files go directly at the root, named by Document Type.
	- Otherwise: files are nested under <EMPLOYEE_ID>/<Document Type>.<ext>
	"""
	zip_buffer = io.BytesIO()
	with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
		for doc in documents:
			try:
				file_path = get_file_path(doc.attachment)
			except Exception:
				continue
			if not file_path or not os.path.isfile(file_path):
				continue

			_, ext = os.path.splitext(file_path)
			safe_doc_type = (doc.document_type or "Document").replace(" ", "_").replace("/", "-")

			if single_employee:
				archive_name = f"{safe_doc_type}{ext}"
			else:
				archive_name = f"{doc.employee}/{safe_doc_type}{ext}"

			zip_file.write(file_path, archive_name)

	zip_buffer.seek(0)
	return zip_buffer


def _send_zip_response(zip_buffer, filename):
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = zip_buffer.getvalue()
	frappe.local.response.type = "binary"


@frappe.whitelist()
def download_company_documents(company, document_type=None):
	"""Download a ZIP of documents for every active employee in a company.
	Optionally restrict to a single Document Type (e.g. only PAN Card).

	Filename:
		<COMPANY>_EMPLOYEE_DOCUMENTS.zip
		<COMPANY>_<DOCUMENT_TYPE>_EMPLOYEE_DOCUMENTS.zip   (when filtered)
	"""
	if not company:
		frappe.throw(_("Company is required."))

	_check_download_permission()

	employees = frappe.get_all(
		"Employee", filters={"company": company, "status": "Active"}, fields=["name"]
	)
	if not employees:
		frappe.throw(_("No active employees found for company {0}").format(company))
	employee_names = [e.name for e in employees]

	documents = _get_documents(employee_names, document_type)
	if not documents:
		msg = _("No documents found for company {0}").format(company)
		if document_type:
			msg = _("No {0} documents found for company {1}").format(document_type, company)
		frappe.throw(msg)

	zip_buffer = _build_zip(documents, single_employee=False)

	company_part = company.upper().replace(" ", "_")
	doc_type_part = f"_{document_type.upper().replace(' ', '_')}" if document_type else ""
	filename = f"{company_part}{doc_type_part}_EMPLOYEE_DOCUMENTS.zip"

	_send_zip_response(zip_buffer, filename)


@frappe.whitelist()
def download_employee_documents(employee, document_type=None):
	"""Download a ZIP of documents for a single employee.
	Optionally restrict to a single Document Type.

	Filename:
		<EMPLOYEE_ID>_DOCUMENTS.zip
		<EMPLOYEE_ID>_<DOCUMENT_TYPE>.zip   (when filtered)
	"""
	if not employee:
		frappe.throw(_("Employee is required."))

	_check_download_permission()

	if not frappe.db.exists("Employee", employee):
		frappe.throw(_("Employee {0} not found.").format(employee))

	documents = _get_documents([employee], document_type)
	if not documents:
		msg = _("No documents found for employee {0}").format(employee)
		if document_type:
			msg = _("No {0} found for employee {1}").format(document_type, employee)
		frappe.throw(msg)

	zip_buffer = _build_zip(documents, single_employee=True)

	doc_type_part = f"_{document_type.upper().replace(' ', '_')}" if document_type else "_DOCUMENTS"
	filename = f"{employee}{doc_type_part}.zip"

	_send_zip_response(zip_buffer, filename)


@frappe.whitelist()
def get_dashboard_data(company=None):
	emp_filters = {"status": "Active"}
	if company:
		emp_filters["company"] = company

	total_employees = frappe.db.count("Employee", filters=emp_filters)
	employee_names = frappe.get_all("Employee", filters=emp_filters, pluck="name")
	if not employee_names:
		return {
			"total_employees": total_employees,
			"documents_uploaded": 0,
			"missing_documents": 0,
			"expired_documents": 0,
			"expiring_in_30_days": 0,
		}

	documents_uploaded = frappe.db.count(
		"Employee Document", filters={"parenttype": "Employee", "parent": ["in", employee_names]}
	)
	expired_documents = frappe.db.count(
		"Employee Document",
		filters={"parenttype": "Employee", "parent": ["in", employee_names], "status": "Expired"},
	)

	cutoff = add_days(today(), 30)
	expiring_in_30_days = frappe.db.sql(
		"""
		select count(*) from `tabEmployee Document`
		where parenttype = 'Employee' and parent in %(employees)s
			and expiry_date is not null and expiry_date between %(today)s and %(cutoff)s
		""",
		{"employees": employee_names, "today": today(), "cutoff": cutoff},
	)[0][0]

	mandatory_types = frappe.get_all("Document Type", filters={"is_mandatory": 1}, pluck="name")
	missing_documents = 0
	if mandatory_types:
		existing_map = {}
		rows = frappe.db.sql(
			"select parent as employee, document_type from `tabEmployee Document` "
			"where parenttype = 'Employee' and parent in %(employees)s and document_type in %(types)s",
			{"employees": employee_names, "types": mandatory_types},
			as_dict=True,
		)
		for row in rows:
			existing_map.setdefault(row.employee, set()).add(row.document_type)
		for emp in employee_names:
			missing_documents += len(set(mandatory_types) - existing_map.get(emp, set()))

	return {
		"total_employees": total_employees,
		"documents_uploaded": documents_uploaded,
		"missing_documents": missing_documents,
		"expired_documents": expired_documents,
		"expiring_in_30_days": expiring_in_30_days,
	}
