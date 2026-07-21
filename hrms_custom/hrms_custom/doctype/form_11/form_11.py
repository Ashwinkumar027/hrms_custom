import re
import frappe
from frappe import _
from frappe.model.document import Document
from hrms_custom.hrms_custom.utils.signature_utils import merge_or_allow_insert

class Form11(Document):
	def validate(self):
		self.validate_aadhar()
		self.validate_pan()
		self.validate_ifsc()
		self.check_read_before_sign()

	def validate_aadhar(self):
		if self.aadhar_number and not re.fullmatch(r"\d{12}", self.aadhar_number):
			frappe.throw(_("Aadhar Number must be exactly 12 digits"))

	def validate_pan(self):
		if self.pan_number and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", self.pan_number.upper()):
			frappe.throw(_("Invalid PAN Number format. Expected format: AAAAA9999A"))

	def validate_ifsc(self):
		if self.ifsc_code and not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", self.ifsc_code.upper()):
			frappe.throw(_("Invalid IFSC Code format"))

	def check_read_before_sign(self):
		if self.signature and self.signature_upload:
			frappe.throw(_("Please choose only one method to sign: either draw your signature or upload one, not both."))

	def before_insert(self):
		merge_or_allow_insert(self, route="Form11")
