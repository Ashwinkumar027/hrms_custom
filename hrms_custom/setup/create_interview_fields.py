import frappe

def create_interview_fields():
    print("\n--- Creating Interview Custom Fields ---")

    fields = [
        {
            "dt": "Interview",
            "fieldname": "custom_interview_mode",
            "fieldtype": "Select",
            "label": "Interview Mode",
            "options": "\nFace to Face\nOnline (Video Call)\nTelephonic\nWalk-in",
            "insert_after": "status",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_interview_location",
            "fieldtype": "Data",
            "label": "Interview Location / Meeting Link",
            "insert_after": "custom_interview_mode",
            "description": "Address for Face to Face or Meeting link for Online",
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_interview_instructions",
            "fieldtype": "Text",
            "label": "Special Instructions for Candidate",
            "insert_after": "custom_interview_location",
            "module": "HRMS Custom"
        },
        {
            "dt": "Interview",
            "fieldname": "custom_notification_sent",
            "fieldtype": "Check",
            "label": "Candidate Notified",
            "insert_after": "custom_interview_instructions",
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
            print("  Created: " + field["label"])
        else:
            print("  Already exists: " + field["label"])

    frappe.db.commit()
    print("Interview fields created!")
