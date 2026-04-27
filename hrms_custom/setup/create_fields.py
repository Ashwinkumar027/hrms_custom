import frappe

def create_job_requisition_fields():
    fields = [
        # ── Section: Position Details ──────────────────
        {
            "dt": "Job Requisition",
            "fieldname": "custom_section_position",
            "fieldtype": "Section Break",
            "label": "Position Details",
            "insert_after": "department",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_hiring_location",
            "fieldtype": "Data",
            "label": "Hiring Location",
            "insert_after": "custom_section_position",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_hiring_manager_name",
            "fieldtype": "Data",
            "label": "Hiring Manager Name",
            "insert_after": "custom_hiring_location",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_hiring_manager_designation",
            "fieldtype": "Data",
            "label": "Hiring Manager Designation",
            "insert_after": "custom_hiring_manager_name",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_type_of_requirement",
            "fieldtype": "Select",
            "label": "Type of Requirement",
            "options": "\nNew Position\nReplacement",
            "insert_after": "custom_hiring_manager_designation",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_position_approval_status",
            "fieldtype": "Select",
            "label": "Position Approval Status",
            "options": "\nYes\nNo",
            "insert_after": "custom_type_of_requirement",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_position_approval_mail",
            "fieldtype": "Attach",
            "label": "Position Approval Mail",
            "description": "If Position Approval Status is Yes, Please attach approval mail.",
            "insert_after": "custom_position_approval_status",
            "depends_on": "eval:doc.custom_position_approval_status=='Yes'",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_position_reporting_to",
            "fieldtype": "Data",
            "label": "Position Reporting To",
            "insert_after": "custom_position_approval_mail",
            "reqd": 1,
            "module": "HRMS Custom"
        },

        # ── Section: Job Description ───────────────────
        {
            "dt": "Job Requisition",
            "fieldname": "custom_section_job_description",
            "fieldtype": "Section Break",
            "label": "Job Description Details",
            "insert_after": "custom_position_reporting_to",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_key_roles",
            "fieldtype": "Text Editor",
            "label": "Key Roles & Responsibilities",
            "insert_after": "custom_section_job_description",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_required_qualifications",
            "fieldtype": "Text Editor",
            "label": "Required Qualifications",
            "insert_after": "custom_key_roles",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_required_experience",
            "fieldtype": "Data",
            "label": "Required Experience",
            "insert_after": "custom_required_qualifications",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_required_skills",
            "fieldtype": "Text Editor",
            "label": "Required Skills / Technical Skills",
            "insert_after": "custom_required_experience",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_preferred_industry",
            "fieldtype": "Data",
            "label": "Preferred Industry (e.g., BFSI, IT, Sales)",
            "insert_after": "custom_required_skills",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_proposed_salary",
            "fieldtype": "Data",
            "label": "Proposed Salary / Budget Range (CTC)",
            "insert_after": "custom_preferred_industry",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Requisition",
            "fieldname": "custom_urgency_level",
            "fieldtype": "Select",
            "label": "Urgency Level",
            "options": "\nHigh — Immediate hiring required\nMedium — Within 30 days\nLow — Can wait 60 days",
            "insert_after": "custom_proposed_salary",
            "reqd": 1,
            "module": "HRMS Custom"
        },
    ]

    for field in fields:
        name = f"{field['dt']}-{field['fieldname']}"
        if not frappe.db.exists("Custom Field", name):
            cf = frappe.new_doc("Custom Field")
            cf.update(field)
            cf.insert(ignore_permissions=True)
            print(f"✅ Created: {field['label']}")
        else:
            print(f"⚠️  Already exists: {field['label']}")

    frappe.db.commit()
    print("\n✅ All Job Requisition fields created successfully!")


def create_job_applicant_fields():
    print("\n--- Creating Job Applicant Custom Fields ---")

    fields = [

        # ── Section: Personal Details ───────────────
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_personal",
            "fieldtype": "Section Break",
            "label": "Personal Details",
            "insert_after": "phone_number",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_date_of_birth",
            "fieldtype": "Date",
            "label": "Date of Birth",
            "insert_after": "custom_section_personal",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_gender",
            "fieldtype": "Select",
            "label": "Gender",
            "options": "\nMale\nFemale\nOthers",
            "insert_after": "custom_date_of_birth",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_marital_status",
            "fieldtype": "Select",
            "label": "Marital Status",
            "options": "\nMarried\nUnmarried\nDivorced\nWidowed",
            "insert_after": "custom_gender",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_languages_known",
            "fieldtype": "Small Text",
            "label": "Languages Known",
            "description": "English, Tamil, Hindi, Telugu, Kannada, Malayalam, Other",
            "insert_after": "custom_marital_status",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_col_break_personal",
            "fieldtype": "Column Break",
            "insert_after": "custom_languages_known",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_current_location",
            "fieldtype": "Data",
            "label": "Current Location",
            "insert_after": "custom_col_break_personal",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_open_to_relocation",
            "fieldtype": "Select",
            "label": "Are you open to relocation?",
            "options": "\nYes\nNo",
            "insert_after": "custom_current_location",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_preferred_location",
            "fieldtype": "Small Text",
            "label": "Preferred Location",
            "description": "Chennai, Bangalore, Trichy, Coimbatore, Madurai, Dubai, Ahmedabad, Namakkal, Singapore, Kanyakumari, Others",
            "insert_after": "custom_open_to_relocation",
            "reqd": 1,
            "module": "HRMS Custom"
        },

        # ── Section: Position Details ───────────────
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_position",
            "fieldtype": "Section Break",
            "label": "Position Details",
            "insert_after": "custom_preferred_location",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_position_applied_for",
            "fieldtype": "Select",
            "label": "Position Applied For",
            "options": (
                "\nSales - Relationship Manager"
                "\nSales - Branch Manager"
                "\nInsurance Executive"
                "\nInsurance Manager"
                "\nHuman Resource Executive"
                "\nClient Care Executive"
                "\nClient Care Manager"
                "\nMIS Executive"
                "\nMIS Manager"
                "\nSales - Business Analyst"
                "\nSales - Corporate Trainer"
                "\nSoft Skill - Corporate Trainer"
                "\nInsurance SME Executive"
                "\nInsurance SME Manager"
                "\nBond Operations Executive"
                "\nMutual Fund Operations"
                "\nSoftware Developer (Frontend / Backend / Full Stack / Mobile App / QA / Data Engineer / DevOps)"
                "\nIT Manager"
                "\nIT Engineer"
                "\nIT Executive"
                "\nDigital Marketing & Graphic Designer"
                "\nVideo Editor"
                "\nContent Writer"
                "\nCameraman"
                "\nAnchor"
                "\nProcess Manager"
                "\nOthers"
            ),
            "insert_after": "custom_section_position",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_experience_level",
            "fieldtype": "Select",
            "label": "Are you a Fresher or Experienced?",
            "options": "\nFresher\nExperienced",
            "insert_after": "custom_position_applied_for",
            "reqd": 1,
            "module": "HRMS Custom"
        },

        # ── Section: Education Details ──────────────
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_education",
            "fieldtype": "Section Break",
            "label": "Education Details",
            "insert_after": "custom_experience_level",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_ug_degree",
            "fieldtype": "Data",
            "label": "UG Degree (With specialization)",
            "description": "Example: B.Com – Finance",
            "insert_after": "custom_section_education",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_pg_degree",
            "fieldtype": "Data",
            "label": "PG Degree (With specialization)",
            "description": "Example: MBA – Finance",
            "insert_after": "custom_ug_degree",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_professional_certifications",
            "fieldtype": "Data",
            "label": "Professional Certifications (if any)",
            "description": "Example: NISM, CFA, CFP, etc.",
            "insert_after": "custom_pg_degree",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_certification_documents",
            "fieldtype": "Attach",
            "label": "Certification Documents",
            "description": "Upload supporting certification documents",
            "insert_after": "custom_professional_certifications",
            "module": "HRMS Custom"
        },

        # ── Section: Declaration ────────────────────
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_declaration",
            "fieldtype": "Section Break",
            "label": "Declaration Section",
            "insert_after": "custom_certification_documents",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_declaration_agreement",
            "fieldtype": "Check",
            "label": "I agree to the above declaration",
            "description": (
                "1. I hereby declare that the information provided "
                "by me in this application form is true and correct "
                "to the best of my knowledge. "
                "2. I understand that any false information or "
                "misrepresentation may lead to rejection of my "
                "application or termination of employment if "
                "discovered later."
            ),
            "insert_after": "custom_section_declaration",
            "reqd": 1,
            "module": "HRMS Custom"
        },
    ]

    for field in fields:
        name = f"{field['dt']}-{field['fieldname']}"
        if not frappe.db.exists("Custom Field", name):
            cf = frappe.new_doc("Custom Field")
            cf.update(field)
            cf.insert(ignore_permissions=True)
            print(f"  ✅ Created: {field.get('label', field['fieldname'])}")
        else:
            print(f"  ⚠️  Already exists: {field.get('label', field['fieldname'])}")

    frappe.db.commit()
    print("\n✅ All Job Applicant fields created successfully!")
def create_pre_offer_fields():
    print("\n--- Creating Pre-Offer Custom Fields in Job Applicant ---")

    fields = [
        # ── Section: KYC / Personal Info ───────────
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_kyc",
            "fieldtype": "Section Break",
            "label": "KYC & Personal Information",
            "insert_after": "custom_declaration_agreement",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_father_spouse_name",
            "fieldtype": "Data",
            "label": "Father / Spouse Name",
            "insert_after": "custom_section_kyc",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_permanent_address",
            "fieldtype": "Text",
            "label": "Permanent Address",
            "insert_after": "custom_father_spouse_name",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_current_address",
            "fieldtype": "Text",
            "label": "Current Address",
            "insert_after": "custom_permanent_address",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_aadhar_number",
            "fieldtype": "Data",
            "label": "Aadhar Number",
            "insert_after": "custom_current_address",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_pan_number",
            "fieldtype": "Data",
            "label": "PAN Number",
            "insert_after": "custom_aadhar_number",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_bank_account_number",
            "fieldtype": "Data",
            "label": "Bank Account Number",
            "insert_after": "custom_pan_number",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_bank_name",
            "fieldtype": "Data",
            "label": "Bank Name",
            "insert_after": "custom_bank_account_number",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_ifsc_code",
            "fieldtype": "Data",
            "label": "IFSC Code",
            "insert_after": "custom_bank_name",
            "reqd": 0,
            "module": "HRMS Custom"
        },

        # ── Section: CTC Details ────────────────────
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_ctc",
            "fieldtype": "Section Break",
            "label": "CTC & Employment Details",
            "insert_after": "custom_ifsc_code",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_current_employer",
            "fieldtype": "Data",
            "label": "Current Employer Name",
            "insert_after": "custom_section_ctc",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_current_designation",
            "fieldtype": "Data",
            "label": "Current Designation",
            "insert_after": "custom_current_employer",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_current_ctc",
            "fieldtype": "Data",
            "label": "Current CTC (Per Annum)",
            "insert_after": "custom_current_designation",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_expected_ctc",
            "fieldtype": "Data",
            "label": "Expected CTC (Per Annum)",
            "insert_after": "custom_current_ctc",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_notice_period",
            "fieldtype": "Select",
            "label": "Notice Period",
            "options": "\nImmediate\n15 Days\n30 Days\n45 Days\n60 Days\n90 Days",
            "insert_after": "custom_expected_ctc",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_last_working_day",
            "fieldtype": "Date",
            "label": "Last Working Day (if already resigned)",
            "insert_after": "custom_notice_period",
            "reqd": 0,
            "module": "HRMS Custom"
        },

        # ── Section: Documents ──────────────────────
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_documents",
            "fieldtype": "Section Break",
            "label": "Document Uploads",
            "insert_after": "custom_last_working_day",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_aadhar_upload",
            "fieldtype": "Attach",
            "label": "Aadhar Card",
            "insert_after": "custom_section_documents",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_pan_upload",
            "fieldtype": "Attach",
            "label": "PAN Card",
            "insert_after": "custom_aadhar_upload",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_10th_marksheet",
            "fieldtype": "Attach",
            "label": "10th Marksheet",
            "insert_after": "custom_pan_upload",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_12th_marksheet",
            "fieldtype": "Attach",
            "label": "12th Marksheet",
            "insert_after": "custom_10th_marksheet",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_sem_marksheet",
            "fieldtype": "Attach",
            "label": "Semester Marksheet",
            "insert_after": "custom_12th_marksheet",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_degree_certificate",
            "fieldtype": "Attach",
            "label": "Degree Certificate",
            "insert_after": "custom_sem_marksheet",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_experience_certificate",
            "fieldtype": "Attach",
            "label": "Experience Certificate",
            "insert_after": "custom_degree_certificate",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_last_salary_slip",
            "fieldtype": "Attach",
            "label": "Last Salary Slip",
            "insert_after": "custom_experience_certificate",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_bank_passbook",
            "fieldtype": "Attach",
            "label": "Bank Passbook / Cancelled Cheque",
            "insert_after": "custom_last_salary_slip",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_other_documents",
            "fieldtype": "Attach",
            "label": "Other Documents (if any)",
            "insert_after": "custom_bank_passbook",
            "reqd": 0,
            "module": "HRMS Custom"
        },
    ]

    for field in fields:
        name = f"{field['dt']}-{field['fieldname']}"
        if not frappe.db.exists("Custom Field", name):
            cf = frappe.new_doc("Custom Field")
            cf.update(field)
            cf.insert(ignore_permissions=True)
            print(f"  ✅ Created: {field.get('label', field['fieldname'])}")
        else:
            print(f"  ⚠️  Already exists: {field.get('label', field['fieldname'])}")

    frappe.db.commit()
    print("\n✅ Pre-Offer fields created successfully!")
