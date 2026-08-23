import frappe

def execute():
    try:
        req = frappe.db.get_value("Job Requisition", "REQ-Administrative Officer-00003", ["workflow_state", "custom_rejection_reason"], as_dict=True)
        print(f"REQ-Administrative Officer-00003 DB State: {req}")
    except Exception as e:
        print(f"Error: {e}")
