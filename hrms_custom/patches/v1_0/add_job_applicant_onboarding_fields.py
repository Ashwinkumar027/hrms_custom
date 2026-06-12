import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Job Applicant": [
			# ---------- Personal Details (insert after custom_languages_known) ----------
			{
				"fieldname": "custom_personal_contact_number",
				"label": "Personal Contact Number",
				"fieldtype": "Data",
				"insert_after": "custom_languages_known",
			},
			{
				"fieldname": "custom_personal_email",
				"label": "Personal Mail ID",
				"fieldtype": "Data",
				"insert_after": "custom_personal_contact_number",
			},
			{
				"fieldname": "custom_blood_group",
				"label": "Blood Group",
				"fieldtype": "Select",
				"options": "\nA+\nA-\nB+\nB-\nAB+\nAB-\nO+\nO-",
				"insert_after": "custom_personal_email",
			},

			# ---------- Family / Emergency (insert after custom_father_spouse_name) ----------
			{
				"fieldname": "custom_spouse_name",
				"label": "Spouse's Name (if married or NA)",
				"fieldtype": "Data",
				"insert_after": "custom_father_spouse_name",
			},
			{
				"fieldname": "custom_fathers_contact_number",
				"label": "Father's Contact Number",
				"fieldtype": "Data",
				"insert_after": "custom_spouse_name",
			},
			{
				"fieldname": "custom_mothers_name",
				"label": "Mother's Name",
				"fieldtype": "Data",
				"insert_after": "custom_fathers_contact_number",
			},
			{
				"fieldname": "custom_mothers_contact_number",
				"label": "Mother's Contact Number",
				"fieldtype": "Data",
				"insert_after": "custom_mothers_name",
			},
			{
				"fieldname": "custom_emergency_contact_name",
				"label": "Emergency Contact - Name of the Person",
				"fieldtype": "Data",
				"insert_after": "custom_mothers_contact_number",
			},
			{
				"fieldname": "custom_emergency_contact_number",
				"label": "Emergency Contact Number",
				"fieldtype": "Data",
				"insert_after": "custom_emergency_contact_name",
			},

			# ---------- Address (insert after custom_current_address) ----------
			{
				"fieldname": "custom_temporary_address",
				"label": "Temporary Address (Door No, Street name, Area, City, Pincode)",
				"fieldtype": "Text",
				"insert_after": "custom_current_address",
			},

			# ---------- Education (insert after custom_section_education) ----------
			{
				"fieldname": "custom_highest_qualification",
				"label": "Highest Qualification",
				"fieldtype": "Data",
				"insert_after": "custom_section_education",
			},
			{
				"fieldname": "custom_year_of_passing",
				"label": "Year of Passing",
				"fieldtype": "Data",
				"insert_after": "custom_highest_qualification",
			},
			{
				"fieldname": "custom_ug_certificate",
				"label": "UG Degree Certificate",
				"fieldtype": "Attach",
				"insert_after": "custom_ug_degree",
			},
			{
				"fieldname": "custom_pg_certificate",
				"label": "PG Degree Certificate",
				"fieldtype": "Attach",
				"insert_after": "custom_pg_degree",
			},

			# ---------- Bank Details (insert after custom_ifsc_code) ----------
			{
				"fieldname": "custom_bank_account_holder_name",
				"label": "Personal Bank (Your Name as per Bank)",
				"fieldtype": "Data",
				"insert_after": "custom_bank_name",
			},
			{
				"fieldname": "custom_bank_branch_name",
				"label": "Bank Branch Name",
				"fieldtype": "Data",
				"insert_after": "custom_bank_account_holder_name",
			},

			# ---------- Professional Details (new section, insert after custom_section_ctc fields) ----------
			{
				"fieldname": "custom_section_professional",
				"label": "Professional Details",
				"fieldtype": "Section Break",
				"insert_after": "custom_last_working_day",
			},
			{
				"fieldname": "custom_last_org_hr_email",
				"label": "Last Organization Common HR Mail ID (For BGV)",
				"fieldtype": "Data",
				"insert_after": "custom_section_professional",
			},
			{
				"fieldname": "custom_last_org_hr_contact",
				"label": "Last Organization HR Contact Number (For BGV)",
				"fieldtype": "Data",
				"insert_after": "custom_last_org_hr_email",
			},
			{
				"fieldname": "custom_relevant_experience",
				"label": "Relevant Experience",
				"fieldtype": "Data",
				"insert_after": "custom_last_org_hr_contact",
			},
			{
				"fieldname": "custom_relatives_in_company",
				"label": "Relatives/Friends working at Aionion?",
				"fieldtype": "Select",
				"options": "\nYes\nNo",
				"insert_after": "custom_relevant_experience",
			},
			{
				"fieldname": "custom_relatives_details",
				"label": "If yes, name and relation (else N/A)",
				"fieldtype": "Data",
				"insert_after": "custom_relatives_in_company",
			},
			{
				"fieldname": "custom_client_of_company",
				"label": "Are you a client of Aionion?",
				"fieldtype": "Select",
				"options": "\nYes\nNo",
				"insert_after": "custom_relatives_details",
			},
			{
				"fieldname": "custom_client_rm_name",
				"label": "If yes, RM name (else N/A)",
				"fieldtype": "Data",
				"insert_after": "custom_client_of_company",
			},
			{
				"fieldname": "custom_uan_number",
				"label": "UAN Number (If Fresher, create one)",
				"fieldtype": "Data",
				"insert_after": "custom_client_rm_name",
			},

			# ---------- Document Uploads (insert after custom_section_documents block) ----------
			{
				"fieldname": "custom_passport_photo",
				"label": "Passport Size Photo",
				"fieldtype": "Attach",
				"insert_after": "custom_aadhar_upload",
			},
			{
				"fieldname": "custom_casual_photo",
				"label": "Casual Photo",
				"fieldtype": "Attach",
				"insert_after": "custom_passport_photo",
			},
			{
				"fieldname": "custom_aadhaar_pan_link_status",
				"label": "Aadhaar-PAN Linking Status Screenshot",
				"fieldtype": "Attach",
				"insert_after": "custom_bank_passbook",
			},
			{
				"fieldname": "custom_psychometric_test_screenshot",
				"label": "Psychometric Test Screenshot",
				"fieldtype": "Attach",
				"insert_after": "custom_aadhaar_pan_link_status",
			},
			{
				"fieldname": "custom_psychometric_factor1",
				"label": "Psychometric Factor 1 (Screenshot)",
				"fieldtype": "Attach",
				"insert_after": "custom_psychometric_test_screenshot",
			},
			{
				"fieldname": "custom_psychometric_factor2",
				"label": "Psychometric Factor 2 (Screenshot)",
				"fieldtype": "Attach",
				"insert_after": "custom_psychometric_factor1",
			},
			{
				"fieldname": "custom_psychometric_factor3",
				"label": "Psychometric Factor 3 (Screenshot)",
				"fieldtype": "Attach",
				"insert_after": "custom_psychometric_factor2",
			},
			{
				"fieldname": "custom_psychometric_factor4",
				"label": "Psychometric Factor 4 (Screenshot)",
				"fieldtype": "Attach",
				"insert_after": "custom_psychometric_factor3",
			},
			{
				"fieldname": "custom_psychometric_factor5",
				"label": "Psychometric Factor 5 (Screenshot)",
				"fieldtype": "Attach",
				"insert_after": "custom_psychometric_factor4",
			},
			{
				"fieldname": "custom_ic38_certified",
				"label": "Have you completed the IC 38 certification?",
				"fieldtype": "Select",
				"options": "\nYes\nNo",
				"insert_after": "custom_psychometric_factor5",
			},
			{
				"fieldname": "custom_has_agency_code",
				"label": "If yes, do you have an agency code?",
				"fieldtype": "Select",
				"options": "\nYes\nNo",
				"insert_after": "custom_ic38_certified",
			},
			{
				"fieldname": "custom_agency_code_screenshot",
				"label": "Agency Code Screenshot",
				"fieldtype": "Attach",
				"insert_after": "custom_has_agency_code",
			},
			{
				"fieldname": "custom_appointment_offer_letter",
				"label": "Last Organization Appointment/Offer Letter",
				"fieldtype": "Attach",
				"insert_after": "custom_last_salary_slip",
			},
			{
				"fieldname": "custom_relieving_letter",
				"label": "Last Organization Experience/Relieving Letter",
				"fieldtype": "Attach",
				"insert_after": "custom_appointment_offer_letter",
			},
			{
				"fieldname": "custom_payslip_month2",
				"label": "Last Salary Slip - Month 2",
				"fieldtype": "Attach",
				"insert_after": "custom_relieving_letter",
			},
			{
				"fieldname": "custom_payslip_month3",
				"label": "Last Salary Slip - Month 3",
				"fieldtype": "Attach",
				"insert_after": "custom_payslip_month2",
			},
		]
	}

	create_custom_fields(custom_fields, update=True)
