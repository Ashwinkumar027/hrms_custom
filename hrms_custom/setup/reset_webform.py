import frappe

def reset_job_application_webform():
    print("\n--- Resetting Job Application Web Form to Original ---")

    wf = frappe.get_doc("Web Form", "job-application")

    original_fields = [
        {
            "fieldname": "job_title",
            "fieldtype": "Data",
            "label": "Job Opening",
            "reqd": 0,
            "read_only": 1,
            "hidden": 0,
        },
        {
            "fieldname": "applicant_name",
            "fieldtype": "Data",
            "label": "Applicant Name",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "email_id",
            "fieldtype": "Data",
            "label": "Email Address",
            "options": "Email",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "phone_number",
            "fieldtype": "Data",
            "label": "Phone Number",
            "options": "Phone",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "country",
            "fieldtype": "Link",
            "label": "Country of Residence",
            "options": "Country",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "cover_letter",
            "fieldtype": "Text",
            "label": "Cover Letter",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "resume_link",
            "fieldtype": "Data",
            "label": "Resume Link",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "",
            "fieldtype": "Section Break",
            "label": "Expected Salary Range per month",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "currency",
            "fieldtype": "Link",
            "label": "Currency",
            "options": "Currency",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "",
            "fieldtype": "Column Break",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "lower_range",
            "fieldtype": "Currency",
            "label": "Lower Range",
            "options": "currency",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "",
            "fieldtype": "Column Break",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "upper_range",
            "fieldtype": "Currency",
            "label": "Upper Range",
            "options": "currency",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
    ]

    # Clear all existing fields
    wf.web_form_fields = []

    # Add only original fields
    for field in original_fields:
        wf.append("web_form_fields", field)

    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"✅ Web Form reset to original! Total fields: {len(original_fields)}")
