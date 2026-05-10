import frappe

def create_interview_candidate_fields():
    print("\n--- Adding Candidate Details to Interview Form ---")

    fields = [
        # Section header
        {
            "dt": "Interview",
            "fieldname": "custom_section_candidate_details",
            "fieldtype": "Section Break",
            "label": "Candidate Details",
            "insert_after": "resume_link",
            "collapsible": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_candidate_position",
            "fieldtype": "Data",
            "label": "Position Applied For",
            "insert_after": "custom_section_candidate_details",
            "fetch_from": "job_applicant.custom_position_applied_for",
            "fetch_if_empty": 1,
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_candidate_current_location",
            "fieldtype": "Data",
            "label": "Current Location",
            "insert_after": "custom_candidate_position",
            "fetch_from": "job_applicant.custom_current_location",
            "fetch_if_empty": 1,
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_candidate_preferred_location",
            "fieldtype": "Small Text",
            "label": "Preferred Location",
            "insert_after": "custom_candidate_current_location",
            "fetch_from": "job_applicant.custom_preferred_location",
            "fetch_if_empty": 1,
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_col_break_candidate",
            "fieldtype": "Column Break",
            "insert_after": "custom_candidate_preferred_location",
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_candidate_current_ctc",
            "fieldtype": "Data",
            "label": "Current CTC",
            "insert_after": "custom_col_break_candidate",
            "fetch_from": "job_applicant.custom_current_ctc",
            "fetch_if_empty": 1,
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_candidate_expected_ctc",
            "fieldtype": "Data",
            "label": "Expected CTC",
            "insert_after": "custom_candidate_current_ctc",
            "fetch_from": "job_applicant.custom_expected_ctc",
            "fetch_if_empty": 1,
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_candidate_notice_period",
            "fieldtype": "Select",
            "label": "Notice Period",
            "options": "\nImmediate\n15 Days\n30 Days\n45 Days\n60 Days\n90 Days",
            "insert_after": "custom_candidate_expected_ctc",
            "fetch_from": "job_applicant.custom_notice_period",
            "fetch_if_empty": 1,
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_candidate_resume",
            "fieldtype": "Attach",
            "label": "Resume",
            "insert_after": "custom_candidate_notice_period",
            "fetch_from": "job_applicant.resume_attachment",
            "fetch_if_empty": 1,
            "read_only": 1,
            "module": "HRMS Custom"
        },
    ]

    for field in fields:
        name = f"{field['dt']}-{field['fieldname']}"
        if not frappe.db.exists("Custom Field", name):
            cf = frappe.new_doc("Custom Field")
            cf.update(field)
            cf.insert(ignore_permissions=True)
            print("  Created: " + field.get("label", field["fieldname"]))
        else:
            print("  Already exists: " + field.get("label", field["fieldname"]))

    frappe.db.commit()
    print("\nCandidate details fields added to Interview!")
