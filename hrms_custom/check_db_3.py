import frappe

def execute():
    try:
        activities = frappe.get_all(
            "Employee Boarding Activity", 
            filters={"parent": "HR-EMP-ONB-2026-00005-2"}, 
            fields=["name", "activity_name", "custom_ticket_id"]
        )
        print(f"Activities found for 00005-2: {len(activities)}")
        
        onb = frappe.get_doc("Employee Onboarding", "HR-EMP-ONB-2026-00005-2")
        print(f"Workflow State: {onb.workflow_state}, Docstatus: {onb.docstatus}")
    except Exception as e:
        print(f"Error: {e}")
