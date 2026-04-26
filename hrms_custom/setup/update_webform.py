import frappe

def update_job_application_webform():
    print("\n--- Updating Job Application Web Form ---")

    wf = frappe.get_doc("Web Form", "job-application")

    # Complete field list — original + custom
    all_fields = [

        # ── Original Fields ─────────────────────────
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
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },

        # ── Section: Personal Details ───────────────
        {
            "fieldname": "",
            "fieldtype": "Section Break",
            "label": "Personal Details",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_date_of_birth",
            "fieldtype": "Date",
            "label": "Date Of Birth",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_gender",
            "fieldtype": "Select",
            "label": "Gender",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_marital_status",
            "fieldtype": "Select",
            "label": "Marital Status",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_languages_known",
            "fieldtype": "Small Text",
            "label": "Languages Known",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_current_location",
            "fieldtype": "Data",
            "label": "Current Location",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_open_to_relocation",
            "fieldtype": "Select",
            "label": "Are you open to relocation?",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_preferred_location",
            "fieldtype": "Small Text",
            "label": "Preferred Location",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },

        # ── Section: Position Details ───────────────
        {
            "fieldname": "",
            "fieldtype": "Section Break",
            "label": "Position Details",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_position_applied_for",
            "fieldtype": "Select",
            "label": "Position Applied For",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_experience_level",
            "fieldtype": "Select",
            "label": "Are you a Fresher or Experienced?",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "source",
            "fieldtype": "Link",
            "label": "Source of Application",
            "options": "Job Applicant Source",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },

        # ── Section: Documents Upload ───────────────
        {
            "fieldname": "",
            "fieldtype": "Section Break",
            "label": "Documents Upload",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "resume_attachment",
            "fieldtype": "Attach",
            "label": "Upload Resume",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_certification_documents",
            "fieldtype": "Attach",
            "label": "Certification Documents (if any)",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },

        # ── Section: Education Details ──────────────
        {
            "fieldname": "",
            "fieldtype": "Section Break",
            "label": "Education Details",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_ug_degree",
            "fieldtype": "Data",
            "label": "UG Degree (With specialization)",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_pg_degree",
            "fieldtype": "Data",
            "label": "PG Degree (With specialization)",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_professional_certifications",
            "fieldtype": "Data",
            "label": "Professional Certifications (if any)",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },

        # ── Section: Salary Expectation ─────────────
        {
            "fieldname": "",
            "fieldtype": "Section Break",
            "label": "Salary Expectation",
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
            "fieldname": "upper_range",
            "fieldtype": "Currency",
            "label": "Upper Range",
            "options": "currency",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },

        # ── Section: Declaration ────────────────────
        {
            "fieldname": "",
            "fieldtype": "Section Break",
            "label": "Declaration Section",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
        },
        {
            "fieldname": "custom_declaration_agreement",
            "fieldtype": "Check",
            "label": "I agree to the above declaration",
            "reqd": 1,
            "read_only": 0,
            "hidden": 0,
        },
    ]

    # Clear all existing fields
    wf.web_form_fields = []

    # Add all fields fresh
    for field in all_fields:
        wf.append("web_form_fields", field)
        print(f"  ✅ Added: {field.get('label', field['fieldtype'])}")

    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"\n✅ Web Form updated! Total fields: {len(all_fields)}")
