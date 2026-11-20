import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, formatdate, money_in_words, flt, getdate, nowdate
from hrms_custom.hrms_custom.utils.signature_utils import merge_or_allow_insert


class EmployeeAgreement(Document):
	def validate(self):
		if self.employee_signature and self.employee_signature_upload:
			frappe.throw(
				_("Please provide only one signature — either draw or upload, not both.")
			)

		if not self.date:
			self.date = today()

		# Ensure place and other fields are populated from employee if available
		if self.employee:
			emp = frappe.db.get_value(
				"Employee",
				self.employee,
				["branch", "ctc", "custom_roles_responsibilities", "date_of_birth", "current_address", "permanent_address", "custom_father_name", "custom_spouse_name", "gender"],
				as_dict=True
			)
			if emp:
				if not self.place and emp.branch:
					city = frappe.db.get_value("Branch", emp.branch, "custom_agreement_city")
					self.place = city or "Chennai"
				if not self.custom_employee_ctc and emp.ctc:
					self.custom_employee_ctc = emp.ctc
				if not self.custom_roles__responsibilities and emp.custom_roles_responsibilities:
					self.custom_roles__responsibilities = emp.custom_roles_responsibilities
				if not self.father_name:
					self.father_name = emp.custom_father_name or emp.custom_spouse_name or ""
				if not self.age and emp.date_of_birth:
					dob = getdate(emp.date_of_birth)
					td = getdate(nowdate())
					self.age = td.year - dob.year - ((td.month, td.day) < (dob.month, dob.day))
				if not self.full_address:
					self.full_address = emp.current_address or emp.permanent_address or ""

	def before_insert(self):
		merge_or_allow_insert(self, route="employee-agreement-form")


@frappe.whitelist()
def get_agreement_context(employee=None, company=None, doc_name=None):
	"""
	Returns all resolved dynamic values for the employment agreement.
	Reads branch city from Branch master (UI editable).
	"""
	data = {
		"place": "Chennai",
		"principal_place": "Chennai, Tamil Nadu, India",
		"company_name": "",
		"company_address": "",
		"company_pan": "",
		"business_description": "financial and corporate services",
		"signatory_name": "",
		"signatory_designation": "",
		"signatory_signature": "",
		"reporting_manager": "the Board",
		"ctc_formatted": "____",
		"ctc_in_words": "____",
		"roles_responsibilities": "",
		"parent_spouse_name": "",
		"relation": "S/o",
		"age": "",
		"full_address": "",
		"execution_date": formatdate(today(), "dd-mm-yyyy"),
		"company_logo": "",
		"cin_number": "",
		"sebi_registration_no": "",
		"compliance_email": "",
		"amfi_registration_no": "",
	}

	ea_doc = None
	if doc_name and frappe.db.exists("Employee Agreement", doc_name):
		ea_doc = frappe.get_doc("Employee Agreement", doc_name)
		if ea_doc.date:
			data["execution_date"] = formatdate(ea_doc.date, "dd-mm-yyyy")
		if ea_doc.place:
			data["place"] = ea_doc.place
		if not employee:
			employee = ea_doc.employee
		if not company:
			company = ea_doc.company

	if employee:
		emp_doc = frappe.get_doc("Employee", employee)
		if not company:
			company = emp_doc.company

		# Branch-to-City lookup from Branch master
		if emp_doc.branch:
			b_vals = frappe.db.get_value(
				"Branch", emp_doc.branch, ["custom_agreement_city", "custom_agreement_state"], as_dict=True
			)
			if b_vals:
				city = (b_vals.custom_agreement_city or "").strip()
				state = (b_vals.custom_agreement_state or "").strip()
				if city:
					if not (ea_doc and ea_doc.place):
						data["place"] = city
					data["principal_place"] = f"{city}, {state}" if state else f"{city}, India"

		# Reporting manager
		if emp_doc.reports_to:
			m_vals = frappe.db.get_value(
				"Employee", emp_doc.reports_to, ["employee_name", "designation"], as_dict=True
			)
			if m_vals and m_vals.employee_name:
				data["reporting_manager"] = f"{m_vals.employee_name} ({m_vals.designation})" if m_vals.designation else m_vals.employee_name

		# CTC formatting
		ctc_val = flt(ea_doc.custom_employee_ctc if (ea_doc and ea_doc.custom_employee_ctc) else emp_doc.ctc)
		if ctc_val > 0:
			data["ctc_formatted"] = f"{ctc_val:,.2f}"
			data["ctc_in_words"] = money_in_words(ctc_val, "INR")

		# Roles and responsibilities
		roles = (ea_doc.custom_roles__responsibilities if (ea_doc and ea_doc.custom_roles__responsibilities) else None)
		if not roles and hasattr(emp_doc, "custom_roles_responsibilities"):
			roles = emp_doc.custom_roles_responsibilities
		data["roles_responsibilities"] = roles or ""

		# Parent / Spouse name & Relation
		spouse = getattr(emp_doc, "custom_spouse_name", None)
		father = getattr(emp_doc, "custom_father_name", None) or (ea_doc.father_name if ea_doc else None)
		gender = (emp_doc.gender or "").lower()

		if spouse:
			data["parent_spouse_name"] = spouse
			data["relation"] = "W/o" if gender == "female" else "H/o"
		elif father:
			data["parent_spouse_name"] = father
			data["relation"] = "D/o" if gender == "female" else "S/o"
		else:
			data["parent_spouse_name"] = "____"
			data["relation"] = "S/o, D/o or W/o"

		# Age calculation
		if ea_doc and ea_doc.age:
			data["age"] = str(ea_doc.age)
		elif emp_doc.date_of_birth:
			dob = getdate(emp_doc.date_of_birth)
			td = getdate(nowdate())
			age_val = td.year - dob.year - ((td.month, td.day) < (dob.month, dob.day))
			data["age"] = str(age_val)

		# Address
		data["full_address"] = (ea_doc.full_address if (ea_doc and ea_doc.full_address) else None) or emp_doc.current_address or emp_doc.permanent_address or ""

	if company:
		comp_name = frappe.db.get_value("Company", company, "company_name")
		data["company_name"] = comp_name or company

		if frappe.db.exists("Offer Letter Print Settings", company):
			settings = frappe.get_doc("Offer Letter Print Settings", company)
			data["company_address"] = settings.registered_address or ""
			data["company_pan"] = getattr(settings, "company_pan", "") or ""
			data["business_description"] = getattr(settings, "business_description", "") or "financial planning and corporate services"
			data["signatory_name"] = settings.signatory_name or ""
			data["signatory_designation"] = settings.signatory_designation or ""
			data["signatory_signature"] = settings.signatory_signature or ""
			data["company_logo"] = settings.company_logo or ""
			data["cin_number"] = settings.cin_number or ""
			data["sebi_registration_no"] = settings.sebi_registration_no or ""
			data["compliance_email"] = settings.compliance_email or ""
			data["amfi_registration_no"] = settings.amfi_registration_no or ""

	return data
