import frappe

def execute():
    try:
        activities = frappe.get_all(
            "Employee Boarding Activity", 
            filters={"parent": "HR-EMP-ONB-2026-00004"}, 
            fields=["name", "activity_name", "custom_ticket_id", "custom_status"]
        )
        print(f"Activities found for Ashwinkumar: {len(activities)}")
        for a in activities:
            print(f"- {a.activity_name}: {a.custom_ticket_id} ({a.custom_status})")
    except Exception as e:
        print(f"Error: {e}")
