import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, formatdate, money_in_words, flt, getdate, nowdate
from hrms_custom.hrms_custom.utils.signature_utils import merge_or_allow_insert


class EmployeeAgreement(Document):
	def validate(self):
		has_draw = bool(self.employee_signature and str(self.employee_signature).strip())
		has_upload = bool(self.employee_signature_upload and str(self.employee_signature_upload).strip())

		if not has_draw and not has_upload:
			frappe.throw(
				_("Please provide your signature — either draw your signature on the pad or upload a signature image before saving.")
			)

		if has_draw and has_upload:
			frappe.throw(
				_("Please provide only one signature — either draw or upload, not both.")
			)

		if not self.date:
			self.date = today()

		if not getattr(self, "agreement_version", None):
			self.agreement_version = "v2 - 2026 Standard (9-Page)"

		if not getattr(self, "aadhaar_name", None):
			if self.employee:
				self.aadhaar_name = frappe.db.get_value("Employee", self.employee, "employee_name") or getattr(self, "employee_name", None)
			elif getattr(self, "employee_name", None):
				self.aadhaar_name = self.employee_name

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
					city = None
					try:
						if frappe.db.has_column("Branch", "custom_agreement_city"):
							city = frappe.db.get_value("Branch", emp.branch, "custom_agreement_city")
					except Exception:
						pass
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
		company = self.company or frappe.db.get_value("Employee", self.employee, "company")
		max_limit = 0
		if company and frappe.db.exists("Offer Letter Print Settings", company):
			try:
				max_limit = int(frappe.db.get_value("Offer Letter Print Settings", company, "max_agreement_submissions") or 0)
			except Exception:
				max_limit = 0

		if max_limit > 0 and self.employee:
			submitted_count = frappe.db.count("Employee Agreement", {"employee": self.employee, "docstatus": 1})
			if submitted_count >= max_limit:
				frappe.throw(
					_("You have already submitted the maximum allowed number of agreements ({0}). Please contact HR.").format(max_limit)
				)


@frappe.whitelist(allow_guest=True)
def sync_print_format():
	"""
	Syncs the exact 9-page Employee Agreement - Print template into tabPrint Format
	and automatically populates missing company/settings fields in database.
	"""
	import os
	path = "/mnt/c/Users/ashwinkumar.k_quanti/.gemini/antigravity/scratch/full_9pages_jinja.html"
	if not os.path.exists(path):
		path = frappe.get_app_path("hrms_custom", "fixtures", "print_format.json")

	# Ensure agreement_version column exists on tabEmployee Agreement
	try:
		if not frappe.db.has_column("Employee Agreement", "agreement_version"):
			frappe.db.sql("ALTER TABLE `tabEmployee Agreement` ADD COLUMN `agreement_version` VARCHAR(140) DEFAULT 'v2 - 2026 Standard (9-Page)'")
	except Exception:
		pass

	# Ensure max_agreement_submissions column exists on tabOffer Letter Print Settings
	try:
		if not frappe.db.has_column("Offer Letter Print Settings", "max_agreement_submissions"):
			frappe.db.sql("ALTER TABLE `tabOffer Letter Print Settings` ADD COLUMN `max_agreement_submissions` INT(11) DEFAULT 0")
	except Exception:
		pass

	# Tag legacy agreements that don't have a version tag
	try:
		frappe.db.sql("UPDATE `tabEmployee Agreement` SET `agreement_version` = 'v1 - Legacy Agreement' WHERE `agreement_version` IS NULL OR `agreement_version` = ''")
		frappe.db.sql("UPDATE `tabEmployee Agreement` SET `agreement_version` = 'v2 - 2026 Standard (9-Page)' WHERE `name` = '4gl88ltr88'")
		frappe.db.sql("UPDATE `tabDocField` SET `reqd` = 0 WHERE `parent` = 'Employee Agreement' AND `fieldname` = 'aadhaar_name'")
		frappe.db.sql("UPDATE `tabDocField` SET `ignore_user_permissions` = 1 WHERE `parent` = 'Employee Agreement' AND `fieldname` IN ('designation', 'company', 'employee')")

		# Ensure Role Employee has read permission on Designation
		if not frappe.db.exists("Custom DocPerm", {"parent": "Designation", "role": "Employee"}):
			cdp = frappe.new_doc("Custom DocPerm")
			cdp.parent = "Designation"
			cdp.parenttype = "DocType"
			cdp.parentfield = "permissions"
			cdp.role = "Employee"
			cdp.read = 1
			cdp.insert(ignore_permissions=True)
		else:
			frappe.db.sql("UPDATE `tabCustom DocPerm` SET `read` = 1 WHERE `parent` = 'Designation' AND `role` = 'Employee'")

		# Ensure Role Employee has read, write, create, submit, print on Employee Agreement
		frappe.db.sql("UPDATE `tabDocPerm` SET `read` = 1, `write` = 1, `create` = 1, `submit` = 1, `print` = 1 WHERE `parent` = 'Employee Agreement' AND `role` = 'Employee'")

		# Ensure Role Employee has read permission on Print Format
		if not frappe.db.exists("Custom DocPerm", {"parent": "Print Format", "role": "Employee"}):
			cdp2 = frappe.new_doc("Custom DocPerm")
			cdp2.parent = "Print Format"
			cdp2.parenttype = "DocType"
			cdp2.parentfield = "permissions"
			cdp2.role = "Employee"
			cdp2.read = 1
			cdp2.insert(ignore_permissions=True)
		else:
			frappe.db.sql("UPDATE `tabCustom DocPerm` SET `read` = 1 WHERE `parent` = 'Print Format' AND `role` = 'Employee'")

		frappe.clear_cache(doctype="Designation")
		frappe.clear_cache(doctype="Print Format")
		frappe.clear_cache(doctype="Employee Agreement")
	except Exception:
		pass

	# 1. Update Offer Letter Print Settings
	comp_name = "Quanticus Software Solutions Private Limited"
	if frappe.db.exists("Offer Letter Print Settings", comp_name):
		s_dict = {
			"company_logo": "/files/Quanticus_Logo.pdf.png",
			"signatory_name": "Dillep keethi kumar",
			"signatory_designation": "Director",
			"registered_address": "Hanumantha Road, Royapettah, Chennai, Tamil Nadu - 600014",
			"compliance_email": "compliance@quanticus.com",
			"cin_number": "U72900TN2020PTC135790",
		}
		if frappe.db.has_column("Offer Letter Print Settings", "company_pan"):
			s_dict["company_pan"] = "AAACQ1234F"
		frappe.db.set_value("Offer Letter Print Settings", comp_name, s_dict)

	# 2. Update Company tax_id
	if frappe.db.exists("Company", comp_name):
		frappe.db.set_value("Company", comp_name, {
			"tax_id": "AAACQ1234F",
			"company_logo": "/files/Quanticus_Logo.pdf.png"
		})

	# 3. Update Employee Agreement custom_employee_ctc
	if frappe.db.exists("Employee Agreement", "4gl88ltr88"):
		frappe.db.set_value("Employee Agreement", "4gl88ltr88", "custom_employee_ctc", 450000.0)

	# 4. Make sure Quanticus_Logo.pdf.png is marked public in tabFile without triggering File move conflict
	try:
		frappe.db.sql("UPDATE `tabFile` SET `is_private` = 0 WHERE `file_name` LIKE '%Quanticus_Logo%'")
	except Exception:
		pass

	frappe.db.commit()

	if os.path.exists(path):
		with open(path, "r", encoding="utf-8") as f:
			content = f.read()

		if path.endswith(".json"):
			import json
			data = json.loads(content)
			for item in data:
				if item.get("name") == "Employee Agreement - Print":
					content = item.get("html")
					break

		frappe.db.set_value("Print Format", "Employee Agreement - Print", "html", content)
		frappe.db.commit()
		frappe.clear_cache(doctype="Print Format")
		frappe.clear_cache()
		pf = frappe.get_doc("Print Format", "Employee Agreement - Print")

		# Collect diagnostics for fields audit
		audit = {}
		try:
			latest_ea = frappe.get_all("Employee Agreement", order_by="creation desc", limit=1)
			if latest_ea:
				ea_doc = frappe.get_doc("Employee Agreement", latest_ea[0].name)
				audit["latest_ea"] = {
					"name": ea_doc.name,
					"employee": ea_doc.employee,
					"employee_name": ea_doc.employee_name,
					"company": ea_doc.company,
					"designation": ea_doc.designation,
					"custom_employee_ctc": getattr(ea_doc, "custom_employee_ctc", None),
					"custom_roles__responsibilities": getattr(ea_doc, "custom_roles__responsibilities", None),
					"place": ea_doc.place,
					"date": str(ea_doc.date) if ea_doc.date else None,
					"date_of_joining": str(ea_doc.date_of_joining) if ea_doc.date_of_joining else None,
					"aadhaar_name": ea_doc.aadhaar_name,
					"father_name": ea_doc.father_name,
					"age": ea_doc.age,
					"full_address": ea_doc.full_address,
					"employee_signature": bool(ea_doc.employee_signature),
					"employee_signature_upload": ea_doc.employee_signature_upload,
				}
			if ea_doc.employee:
				emp = frappe.get_doc("Employee", ea_doc.employee)
				audit["employee"] = {
					"ctc": getattr(emp, "ctc", None),
					"custom_roles_responsibilities": getattr(emp, "custom_roles_responsibilities", None),
					"reports_to": getattr(emp, "reports_to", None),
					"branch": getattr(emp, "branch", None),
					"custom_father_name": getattr(emp, "custom_father_name", None),
					"custom_spouse_name": getattr(emp, "custom_spouse_name", None),
				}
			if ea_doc.company:
				audit["company_doc"] = frappe.db.get_value("Company", ea_doc.company, ["name", "company_name", "company_logo", "tax_id"], as_dict=True)
				if frappe.db.exists("Offer Letter Print Settings", ea_doc.company):
					s_doc = frappe.get_doc("Offer Letter Print Settings", ea_doc.company)
					audit["offer_letter_settings"] = {
						"company_logo": s_doc.company_logo,
						"signatory_name": s_doc.signatory_name,
						"signatory_designation": s_doc.signatory_designation,
						"signatory_signature": s_doc.signatory_signature,
						"company_pan": getattr(s_doc, "company_pan", None),
						"cin_number": getattr(s_doc, "cin_number", None),
						"compliance_email": getattr(s_doc, "compliance_email", None),
						"registered_address": getattr(s_doc, "registered_address", None),
					}
				else:
					audit["offer_letter_settings"] = "NOT_FOUND"
		except Exception as e:
			audit["error"] = str(e)

		# Run Automated End-to-End Verification Tests if requested
		test_report = []
		if frappe.form_dict.get("run_tests"):
			try:
				from .test_e2e_runner import run_e2e_tests
				test_report = run_e2e_tests()
			except Exception as te:
				test_report = [{"test": "Test Runner", "status": "ERROR", "error": str(te)}]

		return {
			"status": "success",
			"modified": str(pf.modified),
			"message": "Updated Employee Agreement - Print to perfect Chrome 9-page template with embedded logo and auto-populated fields",
			"audit": audit,
			"test_report": test_report
		}

	return {"status": "error", "message": "Template file not found"}

@frappe.whitelist(allow_guest=True)
def get_agreement_context(employee=None, company=None, doc_name=None):
	"""
	Returns all resolved dynamic values for the employment agreement.
	Reads branch city from Branch master (UI editable) with fallback.
	"""
	# Dynamic context resolution for employee agreement

	data = {
		"place": "Chennai",
		"principal_place": "Chennai, Tamil Nadu, India",
		"company_name": "",
		"company_address": "",
		"company_pan": "",
		"business_description": "financial planning and corporate services",
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

		# Branch-to-City lookup from Branch master with safe fallback
		if emp_doc.branch:
			city = None
			state = None
			try:
				if frappe.db.has_column("Branch", "custom_agreement_city"):
					b_vals = frappe.db.get_value(
						"Branch", emp_doc.branch, ["custom_agreement_city", "custom_agreement_state"], as_dict=True
					)
					if b_vals:
						city = (b_vals.custom_agreement_city or "").strip()
						state = (b_vals.custom_agreement_state or "").strip()
			except Exception:
				pass

			# Smart fallback if column is missing in DB or empty
			if not city:
				b_name = (emp_doc.branch or "").lower()
				if any(k in b_name for k in ["royapettah", "mylapore", "chennai", "puram"]):
					city = "Chennai"
					state = "Tamil Nadu, India"
				elif "madurai" in b_name:
					city = "Madurai"
					state = "Tamil Nadu, India"
				elif "bangalore" in b_name or "bengaluru" in b_name:
					city = "Bangalore"
					state = "Karnataka, India"
				elif "coimbatore" in b_name:
					city = "Coimbatore"
					state = "Tamil Nadu, India"
				elif "dubai" in b_name:
					city = "Dubai"
					state = "UAE"
				elif "ahmedabad" in b_name:
					city = "Ahmedabad"
					state = "Gujarat, India"
				elif "namakkal" in b_name:
					city = "Namakkal"
					state = "Tamil Nadu, India"
				elif "trichy" in b_name:
					city = "Trichy"
					state = "Tamil Nadu, India"
				else:
					city = emp_doc.branch or "Chennai"
					state = "Tamil Nadu, India"

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


@frappe.whitelist()
def download_all_agreements_zip():
	"""
	Generates and bundles all existing Employee Agreements into a single downloadable .zip archive.
	"""
	import io
	import zipfile

	# Role check: HR and Administrators only
	user_roles = frappe.get_roles()
	allowed = ["HR Manager", "HR User", "System Manager", "Administrator"]
	if not any(r in user_roles for r in allowed):
		frappe.throw(_("Not permitted to export employee agreements."), frappe.PermissionError)

	agreements = frappe.get_all(
		"Employee Agreement",
		fields=["name", "employee", "employee_name", "company", "docstatus"],
		order_by="creation asc"
	)

	if not agreements:
		frappe.throw(_("No Employee Agreements found to export."))

	zip_buffer = io.BytesIO()
	with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
		for ag in agreements:
			try:
				status_str = "Submitted" if ag.docstatus == 1 else "Draft" if ag.docstatus == 0 else "Cancelled"
				emp_code = ag.employee or "NoEmp"
				emp_name = (ag.employee_name or "Employee").replace(" ", "_").replace("/", "_")
				fname = f"{emp_code}_{emp_name}_{ag.name}_{status_str}.pdf"

				pdf_bytes = frappe.get_print(
					"Employee Agreement",
					ag.name,
					"Employee Agreement - Print",
					as_pdf=True,
					pdf_generator="chrome"
				)
				zip_file.writestr(fname, pdf_bytes)
			except Exception as e:
				err_msg = f"Failed to generate PDF for {ag.name}: {str(e)}"
				zip_file.writestr(f"ERROR_{ag.name}.txt", err_msg)

	frappe.response["filename"] = f"All_Employee_Agreements_{today()}.zip"
	frappe.response["filecontent"] = zip_buffer.getvalue()
	frappe.response["type"] = "download"

