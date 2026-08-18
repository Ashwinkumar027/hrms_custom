import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        "Employee Onboarding Activity": [
            {
                "fieldname": "custom_ticket_id",
                "label": "Ticket ID",
                "fieldtype": "Data",
                "insert_after": "user",
                "read_only": 1
            },
            {
                "fieldname": "custom_status",
                "label": "Status",
                "fieldtype": "Select",
                "options": "Pending\nCompleted",
                "default": "Pending",
                "insert_after": "custom_ticket_id",
                "read_only": 1
            }
        ]
    }
    
    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()
    print("Successfully added custom_ticket_id and custom_status to Employee Onboarding Activity")

execute()
