import frappe

def create_pre_offer_webform():
    print("\n--- Creating Pre-Offer Web Form ---")

    if frappe.db.exists("Web Form", "candidate-pre-offer-form"):
        frappe.delete_doc("Web Form", "candidate-pre-offer-form", ignore_permissions=True, force=True)
        print("  Deleted existing form")

    wf = frappe.new_doc("Web Form")
    wf.title = "Candidate Pre-Offer Form"
    wf.name = "candidate-pre-offer-form"
    wf.route = "candidate-pre-offer"
    wf.doc_type = "Job Applicant"
    wf.module = "HRMS Custom"
    wf.published = 1
    wf.login_required = 0
    wf.allow_multiple = 0
    wf.allow_edit = 1
    wf.allow_incomplete = 1
    wf.success_message = "Thank you! Your details have been submitted successfully."

    fields = [
        {"fieldname": "applicant_name", "fieldtype": "Data", "label": "Applicant Name", "reqd": 1, "read_only": 1, "hidden": 0},
        {"fieldname": "email_id", "fieldtype": "Data", "label": "Email Address", "reqd": 1, "read_only": 1, "hidden": 0},
        {"fieldname": "phone_number", "fieldtype": "Data", "label": "Phone Number", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "", "fieldtype": "Section Break", "label": "Personal & KYC Details", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_father_spouse_name", "fieldtype": "Data", "label": "Father / Spouse Name", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_permanent_address", "fieldtype": "Text", "label": "Permanent Address", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_current_address", "fieldtype": "Text", "label": "Current Address", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_aadhar_number", "fieldtype": "Data", "label": "Aadhar Number", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_pan_number", "fieldtype": "Data", "label": "PAN Number", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "", "fieldtype": "Section Break", "label": "Bank Details", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_bank_account_number", "fieldtype": "Data", "label": "Bank Account Number", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_bank_name", "fieldtype": "Data", "label": "Bank Name", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_ifsc_code", "fieldtype": "Data", "label": "IFSC Code", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "", "fieldtype": "Section Break", "label": "CTC & Employment Details", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_current_employer", "fieldtype": "Data", "label": "Current Employer Name", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_current_designation", "fieldtype": "Data", "label": "Current Designation", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_current_ctc", "fieldtype": "Data", "label": "Current CTC (Per Annum)", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_expected_ctc", "fieldtype": "Data", "label": "Expected CTC (Per Annum)", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_notice_period", "fieldtype": "Select", "label": "Notice Period", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_last_working_day", "fieldtype": "Date", "label": "Last Working Day (if already resigned)", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "", "fieldtype": "Section Break", "label": "Document Uploads", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "resume_attachment", "fieldtype": "Attach", "label": "Resume / CV", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_aadhar_upload", "fieldtype": "Attach", "label": "Aadhar Card", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_pan_upload", "fieldtype": "Attach", "label": "PAN Card", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_bank_passbook", "fieldtype": "Attach", "label": "Bank Passbook / Cancelled Cheque", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_10th_marksheet", "fieldtype": "Attach", "label": "10th Marksheet", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_12th_marksheet", "fieldtype": "Attach", "label": "12th Marksheet", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_sem_marksheet", "fieldtype": "Attach", "label": "Semester Marksheet", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_degree_certificate", "fieldtype": "Attach", "label": "Degree Certificate", "reqd": 1, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_experience_certificate", "fieldtype": "Attach", "label": "Experience Certificate", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_last_salary_slip", "fieldtype": "Attach", "label": "Last Salary Slip", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_other_documents", "fieldtype": "Attach", "label": "Other Documents (if any)", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "", "fieldtype": "Section Break", "label": "Declaration", "reqd": 0, "read_only": 0, "hidden": 0},
        {"fieldname": "custom_declaration_agreement", "fieldtype": "Check", "label": "I hereby declare that all information provided is true and correct", "reqd": 1, "read_only": 0, "hidden": 0},
    ]

    for field in fields:
        wf.append("web_form_fields", field)
        print("  Added: " + field.get("label", field["fieldtype"]))

    wf.insert(ignore_permissions=True)
    frappe.db.commit()
    print("\nPre-Offer Web Form created! Total fields: " + str(len(fields)))
    print("URL: /candidate-pre-offer")
