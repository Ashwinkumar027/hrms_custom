import frappe

def create_merge_script():
    print("\n--- Creating Job Applicant Merge Script ---")

    name = "Merge Pre-Offer Form to Job Applicant"

    if frappe.db.exists("Server Script", name):
        frappe.delete_doc("Server Script", name, ignore_permissions=True)
        print("  Deleted existing script")

    script_code = """
if doc.email_id:
    existing = frappe.db.get_value(
        "Job Applicant",
        {"email_id": doc.email_id, "name": ["!=", doc.name]},
        "name",
        order_by="creation asc"
    )

    if existing:
        existing_doc = frappe.get_doc("Job Applicant", existing)

        fields_to_merge = [
            "custom_father_spouse_name",
            "custom_permanent_address",
            "custom_current_address",
            "custom_aadhar_number",
            "custom_pan_number",
            "custom_bank_account_number",
            "custom_bank_name",
            "custom_ifsc_code",
            "custom_current_employer",
            "custom_current_designation",
            "custom_current_ctc",
            "custom_expected_ctc",
            "custom_notice_period",
            "custom_last_working_day",
            "custom_aadhar_upload",
            "custom_pan_upload",
            "custom_10th_marksheet",
            "custom_12th_marksheet",
            "custom_sem_marksheet",
            "custom_degree_certificate",
            "custom_experience_certificate",
            "custom_last_salary_slip",
            "custom_bank_passbook",
            "custom_other_documents",
            "custom_declaration_agreement",
            "resume_attachment",
            "phone_number",
        ]

        for field in fields_to_merge:
            value = doc.get(field)
            if value:
                existing_doc.set(field, value)

        existing_doc.flags.ignore_permissions = True
        existing_doc.save()

        frappe.db.set_value(
            "Job Applicant",
            doc.name,
            "email_id",
            "duplicate_" + doc.email_id
        )

        frappe.msgprint(
            "Pre-Offer data merged to: " + existing,
            indicator="green",
            title="Merged!"
        )
"""

    ss = frappe.new_doc("Server Script")
    ss.name = name
    ss.script_type = "DocType Event"
    ss.reference_doctype = "Job Applicant"
    ss.doctype_event = "After Insert"
    ss.module = "HRMS Custom"
    ss.script = script_code
    ss.disabled = 0
    ss.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  Created: " + name)
    print("Merge script created successfully!")
