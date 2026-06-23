# Copyright (c) 2026, ASHWIN and contributors
# License: mit

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

DOCUMENT_TYPES = [
	{"document_type_name": "PAN Card", "is_mandatory": 1, "is_expiry_based": 0},
	{"document_type_name": "Aadhaar Card", "is_mandatory": 1, "is_expiry_based": 0},
	{"document_type_name": "Passport", "is_mandatory": 0, "is_expiry_based": 1},
	{"document_type_name": "Driving License", "is_mandatory": 0, "is_expiry_based": 1},
	{"document_type_name": "Resume", "is_mandatory": 1, "is_expiry_based": 0},
	{"document_type_name": "Bank Passbook", "is_mandatory": 1, "is_expiry_based": 0},
	{"document_type_name": "Experience Certificate", "is_mandatory": 0, "is_expiry_based": 0},
	{"document_type_name": "Relieving Letter", "is_mandatory": 0, "is_expiry_based": 0},
	{"document_type_name": "Medical Certificate", "is_mandatory": 0, "is_expiry_based": 0},
	{"document_type_name": "Police Verification", "is_mandatory": 0, "is_expiry_based": 0},
	{"document_type_name": "Other", "is_mandatory": 0, "is_expiry_based": 0},
]


def execute():
	frappe.reload_doc("hrms_custom", "doctype", "document_type")
	frappe.reload_doc("hrms_custom", "doctype", "employee_document")

	create_custom_fields(
		{
			"Employee Education": [
				{"fieldname": "certificate_attachment", "fieldtype": "Attach", "label": "Certificate Attachment", "insert_after": "maj_opt_subj"},
				{"fieldname": "certificate_name", "fieldtype": "Data", "label": "Certificate Name", "insert_after": "certificate_attachment"},
			],
			"Employee": [
				{"fieldname": "documents_tab_break", "fieldtype": "Section Break", "label": "Documents", "insert_after": "attendance_device_id", "collapsible": 1},
				{"fieldname": "employee_documents", "fieldtype": "Table", "label": "Documents", "options": "Employee Document", "insert_after": "documents_tab_break"},
			],
		},
		ignore_validate=True,
	)

	for row in DOCUMENT_TYPES:
		if not frappe.db.exists("Document Type", row["document_type_name"]):
			doc = frappe.new_doc("Document Type")
			doc.update(row)
			doc.insert(ignore_permissions=True)

	create_roles()
	setup_doctype_permissions()
	frappe.db.commit()


def create_roles():
	for role in ["HR User", "HR Manager"]:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)


def setup_doctype_permissions():
	"""Employee: read own | HR User: read+upload | HR Manager/System Manager: full"""
	from frappe.permissions import add_permission, update_permission_property

	target_doctype = "Employee"
	role_matrix = {
		"Employee": {"read": 1, "if_owner": 1},
		"HR User": {"read": 1, "write": 1, "create": 1},
		"HR Manager": {"read": 1, "write": 1, "create": 1, "delete": 1},
		"System Manager": {"read": 1, "write": 1, "create": 1, "delete": 1},
	}
	for role, perms in role_matrix.items():
		if not frappe.db.exists("Custom DocPerm", {"parent": target_doctype, "role": role}):
			add_permission(target_doctype, role, 0)
		for prop, value in perms.items():
			update_permission_property(target_doctype, role, 0, prop, value)
