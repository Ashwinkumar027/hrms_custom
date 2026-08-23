import frappe

def execute():
    try:
        script = frappe.db.get_value("Server Script", "job_requisition_workflow_emails", "script")
        print("--- job_requisition_workflow_emails Script ---")
        print(script)
    except Exception as e:
        print(f"Error: {e}")
