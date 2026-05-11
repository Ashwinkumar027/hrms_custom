import frappe

def create_preoffer_button_field():
    print("\n--- Adding Pre-Offer Form fields to Job Applicant ---")

    fields = [
        {
            "dt": "Job Applicant",
            "fieldname": "custom_section_preoffer",
            "fieldtype": "Section Break",
            "label": "Pre-Offer Form",
            "insert_after": "custom_declaration_agreement",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_preoffer_form_sent",
            "fieldtype": "Check",
            "label": "Pre-Offer Form Sent",
            "insert_after": "custom_section_preoffer",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_preoffer_sent_on",
            "fieldtype": "Datetime",
            "label": "Pre-Offer Form Sent On",
            "insert_after": "custom_preoffer_form_sent",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Applicant",
            "fieldname": "custom_preoffer_sent_by",
            "fieldtype": "Link",
            "label": "Sent By",
            "options": "User",
            "insert_after": "custom_preoffer_sent_on",
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
    print("\nPre-Offer fields added!")
