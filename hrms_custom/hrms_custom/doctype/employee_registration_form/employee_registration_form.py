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
                self.check_read_before_sign(
                        signature_field="health_signature",
                        confirm_field="health_declaration_confirm",
                        label="Health Declaration",
                )
                self.check_read_before_sign(
                        signature_field="nda_signature",
                        confirm_field="nda_confirm",
                        label="Non-Disclosure Agreement",
                )
                self.check_read_before_sign(
                        signature_field="bgv_signature",
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
                if self.health_signature and not self.health_date:
                        self.health_date = today()
        def auto_set_nda_date(self):
                if self.nda_signature and not self.nda_date:
                        self.nda_date = today()
        def auto_set_bgv_date(self):
                if self.bgv_signature and not self.bgv_date:
                        self.bgv_date = today()
        def check_read_before_sign(self, signature_field, confirm_field, label):
                signature_value = self.get(signature_field)
                confirm_value = self.get(confirm_field)
                if signature_value and not confirm_value:
                        frappe.throw(
                                _("Please tick 'I have read and understood the above {0}' before signing.").format(label)
                        )
                if not confirm_value:
                        frappe.throw(
                                _("You must confirm that you have read and understood the {0} before saving.").format(label)
                        )
        def before_insert(self):
                if self.employee and frappe.db.exists(
                        "Employee Registration Form", {"employee": self.employee, "docstatus": ["!=", 2]}
                ):
                        frappe.throw(_("An Employee Registration Form already exists for {0}").format(self.employee))
