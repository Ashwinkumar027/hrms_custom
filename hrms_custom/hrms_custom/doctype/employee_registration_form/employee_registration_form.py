import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class EmployeeRegistrationForm(Document):

	def validate(self):
		self.validate_pan()
		self.validate_aadhaar()
		self.validate_mobile()
		self.auto_set_health_signature_date()
		self.auto_set_nda_date()
		self.auto_set_bgv_date()

	def validate_pan(self):
		if self.pan_number and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", self.pan_number.upper()):
			frappe.throw(_("Invalid PAN format"))

	def validate_aadhaar(self):
		if self.aadhaar_number and not re.fullmatch(r"\d{12}", self.aadhaar_number):
			frappe.throw(_("Aadhaar Number must be exactly 12 digits"))

	def validate_mobile(self):
		if self.mobile_main and not re.fullmatch(r"\d{10}", self.mobile_main):
			frappe.throw(_("Main Mobile Number must be exactly 10 digits"))

	def auto_set_health_signature_date(self):
		if self.health_signature and not self.health_date:
			self.health_date = today()

	def auto_set_nda_date(self):
		if self.nda_signature and not self.nda_date:
			self.nda_date = today()

	def auto_set_bgv_date(self):
		if self.bgv_signature and not self.bgv_date:
			self.bgv_date = today()

	def before_insert(self):
		if self.employee and frappe.db.exists(
			"Employee Registration Form", {"employee": self.employee, "docstatus": ["!=", 2]}
		):
			frappe.throw(_("An Employee Registration Form already exists for {0}").format(self.employee))
