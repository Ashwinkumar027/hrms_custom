import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ESIEnrollment(Document):

    def validate(self):
        self.fetch_employee_details()
        self.validate_aadhar()
        self.validate_ifsc()
        self.validate_nominee_share()
        if self.docstatus == 1:
            self.validate_mandatory_attachments()

    def before_insert(self):
        if frappe.db.exists(
            "ESI Enrollment", {"employee": self.employee, "docstatus": ["!=", 2]}
        ):
            frappe.throw(
                _("An ESI/EPF Enrollment already exists for employee {0}").format(self.employee)
            )

    def fetch_employee_details(self):
        if not self.employee:
            return
        emp = frappe.db.get_value(
            "Employee",
            self.employee,
            [
                "employee_name",
                "date_of_birth",
                "date_of_joining",
                "gender",
                "department",
                "designation",
            ],
            as_dict=True,
        )
        if emp:
            self.employee_name = emp.employee_name
            self.date_of_birth = emp.date_of_birth
            self.date_of_joining = emp.date_of_joining
            self.gender = emp.gender
            self.department = emp.department
            self.designation = emp.designation

    def validate_aadhar(self):
        if self.aadhar_number and not re.fullmatch(r"\d{12}", self.aadhar_number):
            frappe.throw(_("Aadhar Number must be exactly 12 digits"))

    def validate_ifsc(self):
        if self.ifsc_code and not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", self.ifsc_code.upper()):
            frappe.throw(_("Invalid IFSC Code format"))

    def validate_nominee_share(self):
        if self.nominee_details:
            total = sum(flt(n.share_percentage) for n in self.nominee_details)
            if total and total != 100:
                frappe.throw(_("Total nominee share percentage must equal 100%. Currently: {0}%").format(total))

    def validate_mandatory_attachments(self):
        required = {
            "aadhar_attached": "Aadhar Copy",
            "bank_proof_attached": "Bank Proof",
            "photo_attached": "Photo",
        }
        missing = [label for field, label in required.items() if not self.get(field)]
        if missing:
            frappe.throw(_("Please attach: {0} before submitting").format(", ".join(missing)))

    def on_submit(self):
        self.status = "Verified"
        self.verified_by = frappe.session.user
        self.verification_date = frappe.utils.today()


@frappe.whitelist()
def get_employee_snapshot(employee):
    """Called from client JS when Employee field changes on the form."""
    emp = frappe.get_doc("Employee", employee)
    return {
        "employee_name": emp.employee_name,
        "date_of_birth": emp.date_of_birth,
        "date_of_joining": emp.date_of_joining,
        "gender": emp.gender,
        "department": emp.department,
        "designation": emp.designation,
        "bank_name": getattr(emp, "bank_name", None),
        "account_number": getattr(emp, "bank_ac_no", None),
        "ifsc_code": getattr(emp, "ifsc_code", None),
    }
