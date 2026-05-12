import frappe

def create_offer_letter_fields():
    print("\n--- Adding Offer Letter fields to Job Offer ---")

    fields = [
        {
            "dt": "Job Offer",
            "fieldname": "custom_section_offer_letter",
            "fieldtype": "Section Break",
            "label": "Offer Letter Status",
            "insert_after": "custom_bh_approval_date",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_offer_sent",
            "fieldtype": "Check",
            "label": "Offer Letter Sent",
            "insert_after": "custom_section_offer_letter",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_offer_sent_on",
            "fieldtype": "Datetime",
            "label": "Offer Sent On",
            "insert_after": "custom_offer_sent",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_offer_sent_by",
            "fieldtype": "Link",
            "label": "Sent By",
            "options": "User",
            "insert_after": "custom_offer_sent_on",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_col_break_offer_status",
            "fieldtype": "Column Break",
            "insert_after": "custom_offer_sent_by",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_offer_response",
            "fieldtype": "Select",
            "label": "Candidate Response",
            "options": "\nAwaiting Response\nAccepted\nRejected",
            "insert_after": "custom_col_break_offer_status",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_offer_responded_on",
            "fieldtype": "Datetime",
            "label": "Responded On",
            "insert_after": "custom_offer_response",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_offer_token",
            "fieldtype": "Data",
            "label": "Offer Token",
            "insert_after": "custom_offer_responded_on",
            "read_only": 1,
            "hidden": 1,
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
            print("  Exists: " + field.get("label", field["fieldname"]))

    frappe.db.commit()
    print("Done!")
