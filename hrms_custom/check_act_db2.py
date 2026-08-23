import frappe

def execute():
    try:
        activities = frappe.get_all(
            "Employee Boarding Activity", 
            filters={"parent": "HR-EMP-ONB-2026-00005-1"}, 
            fields=["name", "activity_name", "custom_ticket_id"]
        )
        print(f"Activities found for HR-EMP-ONB-2026-00005-1: {len(activities)}")
    except Exception as e:
        print(f"Error: {e}")
