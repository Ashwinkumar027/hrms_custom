import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today
from hrms_custom.hrms_custom.utils.signature_utils import merge_or_allow_insert


class EmployeeRegistrationForm(Document):
	def validate(self):
		self.validate_pan()
		self.validate_aadhaar()
		self.validate_mobile()
		self.auto_set_health_signature_date()
		self.auto_set_nda_date()
		self.auto_set_bgv_date()
		self.check_read_before_sign(
			signature_field="health_signature",
			upload_field="health_signature_upload",
			confirm_field="health_declaration_confirm",
			label="Health Declaration",
		)
		self.check_read_before_sign(
			signature_field="nda_signature",
			upload_field="nda_signature_upload",
			confirm_field="nda_confirm",
			label="Non-Disclosure Agreement",
		)
		self.check_read_before_sign(
			signature_field="bgv_signature",
			upload_field="bgv_signature_upload",
			confirm_field="bgv_confirm",
			label="Background Verification Consent",
		)

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
		if (self.health_signature or self.health_signature_upload) and not self.health_date:
			self.health_date = today()

	def auto_set_nda_date(self):
		if (self.nda_signature or self.nda_signature_upload) and not self.nda_date:
			self.nda_date = today()

	def auto_set_bgv_date(self):
		if (self.bgv_signature or self.bgv_signature_upload) and not self.bgv_date:
			self.bgv_date = today()

	def check_read_before_sign(self, signature_field, upload_field, confirm_field, label):
		signature_value = self.get(signature_field)
		upload_value = self.get(upload_field)
		confirm_value = self.get(confirm_field)

		if signature_value and upload_value:
			frappe.throw(
				_("For {0}, please provide only one signature — either draw or upload, not both.").format(label)
			)

		if (signature_value or upload_value) and not confirm_value:
			frappe.throw(
				_("Please tick 'I have read and understood the above {0}' before signing.").format(label)
			)

		if not confirm_value:
			frappe.throw(
				_("You must confirm that you have read and understood the {0} before saving.").format(label)
			)

	def before_insert(self):
		merge_or_allow_insert(self, route="employee-registration-form")
