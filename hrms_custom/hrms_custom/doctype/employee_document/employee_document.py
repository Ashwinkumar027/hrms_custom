# Copyright (c) 2026, ASHWIN and contributors
# License: mit

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

PAN_REGEX = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
AADHAAR_LENGTH = 12
RESUME_ALLOWED_EXT = (".pdf",)
CERT_ALLOWED_EXT = (".pdf", ".jpg", ".jpeg", ".png")


class EmployeeDocument(Document):
	def validate(self):
		self.validate_attachment_extension()
		self.validate_document_number()
		self.set_status_from_expiry()
		self.validate_duplicate()

	def get_max_file_size(self):
		max_mb = frappe.db.get_single_value("HR Settings", "max_document_file_size_mb")
		return (max_mb or 5) * 1024 * 1024

	def validate_attachment_extension(self):
		if not self.attachment:
			return
		file_url = self.attachment.lower()
		doc_type = (self.document_type or "").strip().lower()

		if doc_type == "resume":
			if not file_url.endswith(RESUME_ALLOWED_EXT):
				frappe.throw(_("Resume must be uploaded as a PDF file only."))
		else:
			if not file_url.endswith(CERT_ALLOWED_EXT):
				frappe.throw(_("Only PDF, JPG, or PNG files are allowed for {0}.").format(self.document_type))

		file_doc = frappe.db.get_value("File", {"file_url": self.attachment}, ["file_size"], as_dict=True)
		if file_doc and file_doc.file_size and file_doc.file_size > self.get_max_file_size():
			frappe.throw(_("Attached file exceeds the maximum allowed file size."))

	def validate_document_number(self):
		doc_type = (self.document_type or "").strip().lower()

		if doc_type == "pan card" and self.document_number:
			pan = self.document_number.strip().upper()
			if not re.match(PAN_REGEX, pan):
				frappe.throw(_("Invalid PAN format. Expected format: ABCDE1234F"))
			self.document_number = pan

		if doc_type == "aadhaar card" and self.document_number:
			aadhaar = re.sub(r"\D", "", self.document_number)
			if len(aadhaar) != AADHAAR_LENGTH:
				frappe.throw(_("Aadhaar number must be exactly {0} digits.").format(AADHAAR_LENGTH))
			self.document_number = aadhaar

	def set_status_from_expiry(self):
		if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
			self.status = "Expired"

	def validate_duplicate(self):
		if not self.document_type:
			return
		is_mandatory = frappe.db.get_value("Document Type", self.document_type, "is_mandatory")
		if not is_mandatory:
			return
		if not (self.parenttype and self.parent):
			return

		existing = frappe.db.sql(
			"""
			select count(*) from `tab{child_doctype}`
			where parent = %(parent)s and parenttype = %(parenttype)s
				and parentfield = %(parentfield)s and document_type = %(document_type)s
				and name != %(name)s
			""".format(child_doctype=self.doctype),
			{
				"parent": self.parent,
				"parenttype": self.parenttype,
				"parentfield": self.parentfield,
				"document_type": self.document_type,
				"name": self.name or "",
			},
			as_dict=True,
		)
		if existing and existing[0]["count(*)"] > 0:
			frappe.throw(_("Document Type {0} is already added for this Employee.").format(self.document_type))
